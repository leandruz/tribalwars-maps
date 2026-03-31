# Autor: Leandro Beraldo (Leandruz)
# GitHub: https://github.com/Leandruz/TribalWars-Maps

import pandas as pd
import requests
import re
import os
import sys
import json
import time
from urllib.parse import unquote_plus
from io import StringIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

# --- CONFIGURAÇÕES GLOBAIS ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

COLORS = CONFIG["colors"]

# Local das fontes agora no repositório
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
FONT_ARIAL = os.path.join(FONT_DIR, "arial.ttf")
FONT_ARIAL_BOLD = os.path.join(FONT_DIR, "arialbd.ttf")

def get_font(size, bold=False):
    f_path = FONT_ARIAL_BOLD if bold else FONT_ARIAL
    try:
        return ImageFont.truetype(f_path, size)
    except:
        return ImageFont.load_default()

def normalize_tag(tag):
    tag = str(tag).upper().strip()
    tag = tag.replace('!', 'I').replace('1', 'I').replace('3', 'E').replace('4', 'A').replace('0', 'O')
    tag = re.sub(r'[^A-Z0-9]', '', tag)
    m = re.match(r'^([A-Z]+)\d*$', tag)
    if m: tag = m.group(1)
    return tag if tag else str(tag)

def mute_color(color, amount=0.5):
    """Retorna uma versão mais 'apagada' da cor RGB dada."""
    r, g, b = color
    return (int(r * amount), int(g * amount), int(b * amount))

class TWData:
    def __init__(self, mundo):
        self.mundo = mundo
        self.url_base = f"https://{mundo}.tribalwars.com.br/map"
        self.cache = {}

    def fetch(self, filename):
        if filename in self.cache: return self.cache[filename]
        url = f"{self.url_base}/{filename}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: return pd.DataFrame()
            df = pd.read_csv(StringIO(resp.text), header=None)
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).apply(unquote_plus)
            self.cache[filename] = df
            return df
        except:
            return pd.DataFrame()

def generate_map(mundo, target_path, mode, entity="tribe", metric="points", war_config=None):
    """
    mode: 'ranking', 'dominance_k', 'conquests', 'combat_heatmap', 'losses', 'war'
    entity: 'tribe', 'player'
    metric: 'points', 'oda', 'odd', 'ods', 'xgoal'
    war_config: {"A": "TAG1", "B": "TAG2", "colorA": (R,G,B), "colorB": (R,G,B)}
    """
    data = TWData(mundo)
    print(f"[{mundo}] Processando {mode} - {entity} - {metric} (war_cfg={'sim' if war_config else 'nao'})")
    
    df_village = data.fetch("village.txt")
    df_player = data.fetch("player.txt")
    df_ally = data.fetch("ally.txt")
    
    if df_village.empty or df_player.empty: 
        print(f"Erro ao baixar dados base do {mundo}")
        return

    # Mapear IDs Dinamicamente (Resiliente a colunas extras)
    df_player.columns = list(range(df_player.shape[1])) # id, name, ally, villages, pts, rank
    df_village.columns = list(range(df_village.shape[1])) # id, name, x, y, player, pts
    
    # 1. Preparar Entidades e Ranking
    top_entries = []
    map_id_color = {}
    
    if mode == 'ranking':
        if entity == 'player':
            df_target = df_player.copy()
            label_metric = metric.upper()
            
            # Mapear oda/odd/ods para os nomes oficiais da Inno (att, def, sup)
            metric_map = {"oda": "att", "odd": "def", "ods": "sup"}
            mk = metric_map.get(metric, metric)
            
            if metric == "xgoal":
                start_str = CONFIG.get("server_start_dates", {}).get(mundo)
                if not start_str:
                    print(f"[{mundo}] Erro: server_start_date não configurado para xGoal")
                    return
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                dias = (datetime.now() - start_date).days
                dias = max(dias, 1) # Evitar divisão por zero
                
                df_target['val'] = (pd.to_numeric(df_target[3], errors='coerce') - 1) / dias
                label_metric = "Média de Noblagens por Dia"
            elif metric != "points":
                df_kill = data.fetch(f"kill_{mk}.txt")
                if df_kill.empty: return
                df_kill = df_kill.copy()
                df_kill.columns = [0, 1, 2] # rank, id, score
                df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                df_target = df_target.merge(df_kill, on=0, how='left')
                df_target['val'] = pd.to_numeric(df_target['val'], errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}" # ODA, ODD, ODS
            else:
                df_target['val'] = pd.to_numeric(df_target[4], errors='coerce')
                label_metric = "Pontos"
            
            top15 = df_target.sort_values('val', ascending=False).head(15)
            for i, row in enumerate(top15.itertuples()):
                map_id_color[row[1]] = COLORS[i]
                top_entries.append({'name': row[2], 'val': row.val, 'rank': i+1, 'color': COLORS[i]})
            villages = df_village[df_village[4].isin(map_id_color.keys())]
            target_ids_for_map = df_village[df_village[4].isin(map_id_color.keys())].copy()
            target_ids_for_map['color_key'] = target_ids_for_map[4]

        else: # Tribe Ranking
            df_target = df_ally.copy()
            df_target.columns = [0,1,2,3,4,5,6,7] # id, name, tag, pts_top, pts_total, players, villages, rank
            df_target['family'] = df_target[2].apply(normalize_tag)
            label_metric = metric.upper()
            
            # Mapear oda/odd para os nomes oficiais da Inno (att, def)
            metric_map = {"oda": "att", "odd": "def"}
            mk = metric_map.get(metric, metric)
            
            if metric != "points":
                df_kill = data.fetch(f"kill_{mk}_tribe.txt")
                if df_kill.empty: return
                df_kill = df_kill.copy()
                df_kill.columns = [0, 1, 2] # rank, id, score
                df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                df_target = df_target.merge(df_kill, on=0, how='left')
                df_target['val'] = pd.to_numeric(df_target['val'], errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}" # ODA, ODD
            else:
                df_target['val'] = pd.to_numeric(df_target[4], errors='coerce')
                label_metric = "total de aldeias"
            
            fams = df_target.groupby('family')['val'].sum().reset_index().sort_values('val', ascending=False).head(15)
            for i, row in enumerate(fams.itertuples()):
                map_id_color[row.family] = COLORS[i]
                top_entries.append({'name': row.family, 'val': row.val, 'rank': i+1, 'color': COLORS[i]})
            
            df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
            df_v = df_village.merge(df_p, on=4, how='left')
            df_v['family'] = df_v['ally_id'].map(df_target.set_index(0)['family'])
            target_ids_for_map = df_v[df_v['family'].isin(map_id_color.keys())].copy()
            target_ids_for_map['color_key'] = target_ids_for_map['family']

    elif mode == 'dominance_k':
        # Dominance logic
        df_v = df_village.copy()
        df_v['K'] = (df_v[3] // 100) * 10 + (df_v[2] // 100)
        df_v = df_v[df_v[4] != 0] # Sem bárbaras
        
        if entity == 'player':
            counts = df_v.groupby(['K', 4]).size().reset_index(name='c')
            total_k = df_v.groupby('K').size().reset_index(name='total')
            counts = counts.merge(total_k, on='K')
            counts['pct'] = (counts['c'] / counts['total']) * 100
            
            best_in_k = counts.sort_values(['K', 'pct'], ascending=[True, False]).groupby('K').head(2)
            player_names = df_player.set_index(0)[1].to_dict()
            
            # Ranking global do TOP 15 dominantes pra legenda
            global_rank = counts.groupby(4)['c'].sum().reset_index().sort_values('c', ascending=False).head(15)
            for i, r in enumerate(global_rank.itertuples()):
                map_id_color[r[1]] = COLORS[i]
                top_entries.append({'name': player_names.get(r[1], "N/A"), 'val': (r.c / df_v.shape[0])*100, 'rank': i+1, 'color': COLORS[i]})
            
            draw_data_k = []
            for k in range(100):
                k_rows = best_in_k[best_in_k['K'] == k]
                if k_rows.empty: continue
                info = []
                for _, row in k_rows.iterrows():
                    info.append({'name': player_names.get(row[4], "N/A"), 'pct': row['pct'], 'color': map_id_color.get(row[4], (255,255,255))})
                draw_data_k.append({'K': k, 'best': info})
                
        else: # Tribe Dominance
            df_target = df_ally.copy()
            df_target.columns = [0,1,2,3,4,5,6,7]
            df_target['family'] = df_target[2].apply(normalize_tag)
            map_aid_fam = df_target.set_index(0)['family'].to_dict()
            
            df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
            df_v = df_v.merge(df_p, on=4, how='left')
            df_v['family'] = df_v['ally_id'].map(map_aid_fam)
            
            counts = df_v.groupby(['K', 'family']).size().reset_index(name='c')
            total_k = df_v.groupby('K').size().reset_index(name='total')
            counts = counts.merge(total_k, on='K')
            counts['pct'] = (counts['c'] / counts['total']) * 100
            
            best_in_k = counts.sort_values(['K', 'pct'], ascending=[True, False]).groupby('K').head(2)
            
            global_rank = counts.groupby('family')['c'].sum().reset_index().sort_values('c', ascending=False).head(15)
            for i, r in enumerate(global_rank.itertuples()):
                map_id_color[r.family] = COLORS[i]
                top_entries.append({'name': r.family, 'val': (r.c / df_v.shape[0])*100, 'rank': i+1, 'color': COLORS[i]})
            
            draw_data_k = []
            for k in range(100):
                k_rows = best_in_k[best_in_k['K'] == k]
                if k_rows.empty: continue
                info = []
                for _, row in k_rows.iterrows():
                    info.append({'name': row['family'], 'pct': row['pct'], 'color': map_id_color.get(row['family'], (255,255,255))})
                draw_data_k.append({'K': k, 'best': info})
        
        label_metric = "Dominancia Global %"

    elif mode == 'conquests':
        # Conquests 24h
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time())
        df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        
        df_target = df_ally.copy()
        df_target.columns = [0,1,2,3,4,5,6,7]
        df_target['family'] = df_target[2].apply(normalize_tag)
        map_aid_fam = df_target.set_index(0)['family'].to_dict()
        map_pid_aid = df_player.set_index(0)[2].to_dict()
        
        df_conq.loc[:, 'new_aid'] = df_conq['new'].map(map_pid_aid)
        df_conq.loc[:, 'fam'] = df_conq['new_aid'].map(map_aid_fam)
        
        counts = df_conq[df_conq['fam'].notna()].groupby('fam').size().reset_index(name='c').sort_values('c', ascending=False).head(15)
        for i, r in enumerate(counts.itertuples()):
            map_id_color[r.fam] = COLORS[i]
            top_entries.append({'name': r.fam, 'val': r.c, 'rank': i+1, 'color': COLORS[i]})
        
        label_metric = "Total de Conquistas"
        
        df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
        df_v = df_village.merge(df_p, on=4, how='left')
        df_v['family'] = df_v['ally_id'].map(map_aid_fam)
        
        # Para conquistas, o mapa de fundo (cloud) é a família, os pontos são as conquistas
        target_ids_for_map = df_v[df_v['family'].isin(map_id_color.keys())].copy()
        target_ids_for_map['color_key'] = target_ids_for_map['family']
        
        villages_conq = df_village[df_village[0].isin(df_conq['vid'])].merge(df_conq, left_on=0, right_on='vid')
        villages_conq['color'] = villages_conq['fam'].map(map_id_color)
        
        # Filtra apenas noblagens das famílias Top 15 (conforme pedido do usuário)
        villages_conq = villages_conq.dropna(subset=['color'])

    elif mode == 'combat_heatmap':
        # Mapa de Calor de Combates (Todas as conquistas 24h)
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time())
        df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        
        # Mapeia vilas para coordenadas
        villages_conq = df_village[df_village[0].isin(df_conq['vid'])].merge(df_conq, left_on=0, right_on='vid')
        
        # Mapeia Tribos dos jogadores (novo e antigo)
        df_p_simple = df_player[[0, 2]].rename(columns={0: 'pid', 2: 'aid'})
        villages_conq = villages_conq.merge(df_p_simple.rename(columns={'pid': 'new', 'aid': 'new_aid'}), on='new', how='left')
        villages_conq = villages_conq.merge(df_p_simple.rename(columns={'pid': 'old', 'aid': 'old_aid'}), on='old', how='left')
        
        # Preencher NaNs (Aldeias bárbaras ou sem tribo)
        villages_conq['new_aid'] = villages_conq['new_aid'].fillna(0).astype(int)
        villages_conq['old_aid'] = villages_conq['old_aid'].fillna(0).astype(int)
        
        label_metric = "Zonas de Combate"
        top_entries = [] # Sem legenda de ranking para heatmap

    elif mode == 'losses':
        # Ranking de Jogadores que mais perderam aldeias
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time())
        df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        
        # 1. Ranking de Jogadores (por quantidade de aldeias perdidas)
        df_victims = df_conq[df_conq["old"] != 0].copy()
        
        # Merge com df_village para obter pontos de cada aldeia
        df_v_pts = df_village[[0, 5]].rename(columns={0: 'vid', 5: 'pts_v'})
        df_victims = df_victims.merge(df_v_pts, on='vid', how='left')
        df_victims['pts_v'] = pd.to_numeric(df_victims['pts_v'], errors='coerce').fillna(0)
        
        # Agrupar por perdedor
        stats_victims = df_victims.groupby("old").agg({'vid': 'count', 'pts_v': 'sum'}).reset_index()
        stats_victims = stats_victims.rename(columns={'vid': 'c', 'pts_v': 'p'}).sort_values('c', ascending=False).head(15)
        
        player_names = df_player.set_index(0)[1].to_dict()
        for i, r in enumerate(stats_victims.itertuples()):
            map_id_color[r.old] = COLORS[i]
            top_entries.append({
                'name': player_names.get(r.old, f"ID:{r.old}"), 
                'val': r.c, 
                'val_pts': r.p,
                'rank': i+1, 
                'color': COLORS[i]
            })
        
        label_metric = "Aldeias e Pontos Perdidos (24h)"
        
        # 1. Aldeias Atuais dos Perdedores
        df_v_current = df_village[df_village[4].isin(map_id_color.keys())].copy()
        df_v_current['color_key'] = df_v_current[4]
        target_ids_for_map = df_v_current
        
        # 2. Aldeias Perdidas (Coordenadas via merge com village.txt original)
        villages_conq = df_village[df_village[0].isin(df_victims['vid'])].merge(df_victims, left_on=0, right_on='vid')
        villages_conq = villages_conq[villages_conq['old'].isin(map_id_color.keys())].copy()
        villages_conq['color'] = villages_conq['old'].map(map_id_color)

    elif mode == 'war' and war_config:
        # Modo Confronto Dinâmico (Tribo A vs Tribo B)
        df_target = df_ally.copy()
        df_target.columns = list(range(df_target.shape[1]))
        df_target['family'] = df_target[2].apply(normalize_tag)
        
        tag_a = normalize_tag(war_config.get("A", "A"))
        tag_b = normalize_tag(war_config.get("B", "B"))
        col_a = war_config.get("color_a", (220, 20, 20)) # Vermelho
        col_b = war_config.get("color_b", (20, 100, 220)) # Azul
        
        map_id_color[tag_a] = col_a
        map_id_color[tag_b] = col_b
        
        # Ranking Legenda (Apenas os dois combatentes)
        map_aid_fam = df_target.set_index(0)['family'].to_dict()
        top_entries.append({'name': f"Família {tag_a}", 'val': 0, 'rank': 1, 'color': col_a})
        top_entries.append({'name': f"Família {tag_b}", 'val': 0, 'rank': 2, 'color': col_b})
        
        label_metric = f"Confronto: {tag_a} vs {tag_b}"
        
        # Mapear aldeias
        df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
        df_v = df_village.merge(df_p, on=4, how='left')
        df_v['family'] = df_v['ally_id'].map(map_aid_fam)
        
        # Identifica vilas combatentes
        target_ids_for_map = df_v[df_v['family'].isin([tag_a, tag_b])].copy()
        target_ids_for_map['color_key'] = target_ids_for_map['family']
        
        # Calcular contagem para legenda
        count_a = target_ids_for_map[target_ids_for_map['family'] == tag_a].shape[0]
        count_b = target_ids_for_map[target_ids_for_map['family'] == tag_b].shape[0]
        top_entries = [] # Reset e re-add com valores
        top_entries.append({'name': f"Família {tag_a}", 'val': count_a, 'rank': 1, 'color': col_a})
        top_entries.append({'name': f"Família {tag_b}", 'val': count_b, 'rank': 2, 'color': col_b})
        fams_context = df_target.groupby('family')[6].sum().reset_index().sort_values(6, ascending=False).head(15)['family'].tolist()
        context_ids = df_v[df_v['family'].isin(fams_context) & ~df_v['family'].isin([tag_a, tag_b])].copy()
        context_ids['color_key'] = 'context'
        map_id_color['context'] = (100, 100, 100) # Cinza Mudo
        
        # Fundir para o desenho das nuvens (contexto + combatentes)
        clouds_data = pd.concat([context_ids, target_ids_for_map])

    # --- DESENHO ARTÍSTICO ---
    # 1. Bounding Box
    if mode == 'dominance_k':
        box_v = df_village[df_village[4] != 0]
    elif mode in ['combat_heatmap', 'losses']:
        box_v = villages_conq
    elif mode == 'war':
        box_v = target_ids_for_map
    else:
        box_v = target_ids_for_map

    if box_v.empty: x_min, x_max, y_min, y_max = 0, 999, 0, 999
    else:
        x_min, x_max = int(box_v[2].min()-30), int(box_v[2].max()+30)
        y_min, y_max = int(box_v[3].min()-30), int(box_v[3].max()+30)
    
    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(999, x_max), min(999, y_max)
    
    w_dim, h_dim = x_max - x_min, y_max - y_min
    escala = 1000 / max(w_dim, h_dim, 1)
    off_x = (1000 - w_dim * escala) / 2
    off_y = (1000 - h_dim * escala) / 2

    def map_xy(x, y):
        return int((x - x_min) * escala + off_x), int((y - y_min) * escala + off_y)

    # Canvas
    legenda_w = 450
    if mode == 'combat_heatmap': legenda_w = 0 # Heatmap sem legenda lateral por enquanto
    img = Image.new('RGBA', (1000 + legenda_w, 1000), (93, 113, 27, 255))
    draw = ImageDraw.Draw(img)
    if legenda_w > 0:
        draw.rectangle([1000, 0, 1000+legenda_w, 1000], fill=(237, 217, 174, 255)) # Fundo TW
    
    # Grade
    for b in range(0, 1000, 100):
        mx, _ = map_xy(b, 0); _, my = map_xy(0, b)
        if 0 <= mx <= 1000: draw.line([(mx, 0), (mx, 1000)], fill=(45, 65, 15, 255))
        if 0 <= my <= 1000: draw.line([(0, my), (1000, my)], fill=(45, 65, 15, 255))
    draw.line([(1000, 0), (1000, 1000)], fill=(0,0,0,255), width=2)

    # 2. Camadas do Mapa
    if mode == 'combat_heatmap':
        overlay = Image.new('RGBA', (1000+legenda_w, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        for r in villages_conq.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            
            # Lógica de Cores solicitada:
            # 1. Noblagem entre tribos (Guerra) -> Vermelho forte
            if r.new_aid != 0 and r.old_aid != 0 and r.new_aid != r.old_aid:
                cor_calor = (220, 20, 20)
                raio_ext = 12
                raio_int = 5
                alpha_ext = 70
                alpha_int = 150
            # 2. Noblagem de sem tribo ou bárbara -> Marrom claro
            else:
                cor_calor = (140, 100, 70)
                raio_ext = 8
                raio_int = 3
                alpha_ext = 50
                alpha_int = 100
                
            # Desenha "aura" externa e "núcleo" interno mais forte
            o_draw.ellipse([x-raio_ext, y-raio_ext, x+raio_ext, y+raio_ext], fill=cor_calor + (alpha_ext,))
            o_draw.ellipse([x-raio_int, y-raio_int, x+raio_int, y+raio_int], fill=cor_calor + (alpha_int,))
        
        # Reduzido o blur de 6 para 2 para dar mais definição técnica
        overlay = overlay.filter(ImageFilter.GaussianBlur(6))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

    elif mode == 'losses':
        # 1. Desenha aldeias REESTANTES (Opacas)
        overlay = Image.new('RGBA', (1000+legenda_w, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        
        # Cloud (Mais suave/opaca)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor_base = map_id_color[r.color_key]
            cor_opaca = mute_color(cor_base, amount=0.5)
            o_draw.ellipse([x-10, y-10, x+10, y+10], fill=cor_opaca + (255,))
        
        # Blur antigo/padrao (15 e as vezes mto, vamos de 12 para nao brilhar demais)
        overlay = overlay.filter(ImageFilter.GaussianBlur(12))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Pontos Atuais (Opacos)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor_base = map_id_color[r.color_key]
            cor_opaca = mute_color(cor_base, amount=0.6)
            draw.ellipse([x-2, y-2, x+2, y+2], fill=cor_opaca + (255,))

        # 2. Desenha aldeias PERDIDAS (Cor Forte e Vibrante)
        for r in villages_conq.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor_forte = map_id_color[r.old]
            # Círculo maior (+3px -> raio 5)
            draw.ellipse([x-5, y-5, x+5, y+5], fill=tuple(cor_forte) + (255,), outline=(255,255,255,200), width=1)

    elif mode == 'war':
        # 1. Desenha Contexto e Clouds
        overlay = Image.new('RGBA', (1000+legenda_w, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        
        # Desenha clouds de todos os envolvidos (War + Contexto)
        for r in clouds_data.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = tuple(map_id_color[r.color_key])
            if r.color_key == 'context':
                o_draw.ellipse([x-6, y-6, x+6, y+6], fill=cor + (100,)) # Contexto mais fraco
            else:
                o_draw.ellipse([x-10, y-10, x+10, y+10], fill=cor + (255,))
        
        overlay = overlay.filter(ImageFilter.GaussianBlur(15))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # 2. Desenha pontos reais
        # A. Contexto (Pontos pequenos)
        for r in context_ids.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(80,80,80,255))
            
        # B. Combatentes (Pontos normais)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = tuple(map_id_color[r.color_key])
            draw.ellipse([x-2, y-2, x+2, y+2], fill=cor + (255,))

    elif mode != 'dominance_k':
        overlay = Image.new('RGBA', (1000+legenda_w, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        dots = Image.new('RGBA', (1000+legenda_w, 1000), (0,0,0,0))
        d_draw = ImageDraw.Draw(dots)
        
        # Cloud (Background)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = tuple(map_id_color[r.color_key])
            o_draw.ellipse([x-10, y-10, x+10, y+10], fill=cor + (255,))
        
        # Aplica Blur
        overlay = overlay.filter(ImageFilter.GaussianBlur(1))
        alpha = overlay.getchannel('A').point(lambda i: int(i * 0.35))
        overlay.putalpha(alpha)
        img = Image.alpha_composite(img, overlay)
        
        # Dots (Foreground)
        source_dots = villages_conq if mode == 'conquests' else target_ids_for_map
        for r in source_dots.itertuples():
            xx = r[3] # Coluna X da vila (índice 2+1)
            yy = r[4] # Coluna Y da vila (índice 3+1)
            x, y = map_xy(xx, yy)
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = r.color if mode == 'conquests' else map_id_color[r.color_key]
            cor = tuple(cor)
            d_draw.ellipse([x-2, y-2, x+3, y+3], fill=cor + (255,), outline=(0,0,0,255))
        img = Image.alpha_composite(img, dots)
        draw = ImageDraw.Draw(img)

    else: # Dominance K drawing
        f_k_bold = get_font(12, bold=True)
        f_k_small = get_font(8, bold=False)
        for k_data in draw_data_k:
            kx, ky = k_data['K'] % 10 * 100, k_data['K'] // 10 * 100
            x1, y1 = map_xy(kx, ky)
            x2, y2 = map_xy(kx+100, ky+100)
            
            # Centralizar Texto no Box
            cx = (x1 + x2) // 2
            draw.text((x1+5, y1+5), f"K{k_data['K']}", fill=(0,0,0,120), font=get_font(10))
            
            ty = y1 + 35
            for best in k_data['best']:
                t_str = f"{best['name'][:10]}"
                p_str = f"{best['pct']:.1f}%"
                cor_k = tuple(best['color'])
                
                # Nome centralizado
                draw.text((cx, ty), t_str, fill=cor_k + (255,), font=f_k_bold, anchor="mm")
                # PCT centralizado logo abaixo
                draw.text((cx, ty+12), p_str, fill=cor_k + (255,), font=f_k_small, anchor="mm")
                ty += 28

    # 3. Legenda (Novo Layout 3 linhas)
    tx, ty = 1015, 25
    tit_mundo = mundo.upper()
    
    # 1ª Linha: Servidor
    draw.text((tx, ty), tit_mundo, fill=(20,20,20), font=get_font(28, True)); ty += 35
    
    # 2ª Linha: Título Principal (Métrica)
    main_tit = f"Ranking por {label_metric}"
    if metric == 'xgoal': main_tit = label_metric
    elif mode == 'dominance_k': main_tit = "Dominância do Mundo"
    elif mode == 'conquests': main_tit = "Conquistas (24h)"
    elif mode == 'combat_heatmap': main_tit = "Mapa de Calor: Combates (24h)"
    elif mode == 'war': main_tit = "Confronto de Tribos"
    draw.text((tx, ty), main_tit, fill=(20,20,20), font=get_font(22, True)); ty += 30
    
    # 3ª Linha: Subtítulo (Categoria/Destaque)
    sub_tit = f"Top 15 {'Famílias' if entity=='tribe' else 'Jogadores'}"
    if mode == 'dominance_k': sub_tit = "Por Continente"
    draw.text((tx, ty), sub_tit, fill=(80,80,80), font=get_font(18, True)); ty += 45
    
    # Detalhe extra
    sub = "Atualizado diariamente"
    draw.text((tx, ty), sub, fill=(120,120,120), font=get_font(14, False)); ty += 25
    draw.line([(tx, ty), (1000+legenda_w-15, ty)], fill=(160,160,160), width=1); ty += 20
    
    for r in top_entries:
        if metric == "xgoal":
            val_str = f"{r['val']:.2f} aldeias/dia"
        elif mode == 'losses':
            pts_fmt = f"{int(r['val_pts']):,}".replace(',', '.')
            val_str = f"{int(r['val'])} ald; -{pts_fmt} pts"
        elif mode == 'war':
            val_str = f"{int(r['val'])} aldeias"
        else:
            val_str = f"{int(r['val']):,}".replace(',', '.')
            
        if mode == 'dominance_k': val_str = f"{r['val']:.2f}%"
        draw.rectangle([tx, ty+3, tx+16, ty+19], fill=tuple(r['color'])+(255,))
        draw.text((tx + 25, ty), f"{r['rank']}. {r['name']} ({val_str})", fill=(0,0,0), font=get_font(18, True))
        ty += 35

    # Footer
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    draw.text((1000+legenda_w-180, 975), f"Atualização: {stamp}", fill=(80,80,80), font=get_font(12))
    
    # Save
    if mode == 'ranking':
        entity_name = "jogadores" if entity == 'player' else "familias"
        metric_part = f"_{metric}" if metric != "points" else ""
        f_name = f"mapa_top15{metric_part}_{entity_name}_{mundo}.png"
    elif mode == 'conquests':
        f_name = f"mapa_top15_conquistas_{mundo}.png"
    elif mode == 'dominance_k':
        if entity == 'player':
            f_name = f"mapa_top15_dominancia_jogadores_K_{mundo}.png"
        else:
            f_name = f"mapa_top15_dominancia_K_{mundo}.png"
    elif mode == 'combat_heatmap':
        f_name = f"mapa_calor_combate_{mundo}.png"
    elif mode == 'losses':
        f_name = f"mapa_top15_perdas_{entity}_{mundo}.png"
    elif mode == 'war':
        f_name = f"mapa_confronto_{mundo}.png"
    
    os.makedirs(target_path, exist_ok=True)
    img.save(os.path.join(target_path, f_name))
    print(f"Finalizado: {f_name}")

if __name__ == "__main__":
    # Teste rápido se chamado sozinho
    generate_map("br140", ".", "ranking", "player", "oda")
