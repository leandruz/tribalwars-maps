# Autor: Leandro Beraldo (Leandruz)
# GitHub: https://github.com/Leandruz/TribalWars-Maps

import pandas as pd
import requests
import re
import os
import sys
import json
import time
import numpy as np
from urllib.parse import unquote_plus
from io import StringIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

# --- CONFIGURAÇÕES GLOBAIS ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

COLORS = CONFIG["colors"]

# Siglas de Servidores -> Domínios Oficiais
DOMAINS = {
    ".BR": "tribalwars.com.br",
    ".PT": "tribalwars.com.pt",
    ".NET": "tribalwars.net",
    ".DS": "die-staemme.de"
}

# Dicionário de Tradução (Interface dos Mapas)
TEXTS = {
    "pt": {
        "ranking": "Ranking por {label}",
        "tribe": "Famílias",
        "player": "Jogadores",
        "dominance_world": "Dominância do Mundo",
        "conquests_24h": "Conquistas (24h)",
        "heatmap": "Mapa de Calor: Combates (24h)",
        "war": "Confronto de Tribos",
        "update": "Atualização",
        "daily": "Atualizado diariamente",
        "continent": "Por Continente",
        "points": "Pontos",
        "avg_noblings": "Média de Noblagens/Dia",
        "combat_zones": "Zonas de Combate",
        "per_day": "aldeias/dia",
        "villages": "aldeias",
        "pts": "pts",
        "alt_total": "total de aldeias",
        "tactical_analysis": "Análise Tática (K)",
        "hot_spot_label": "Ponto Quente: Continente {k}",
        "hot_spot_desc": "({n} noblagens na região)",
        "advance_label": "Avanço: {fam} no {k}",
        "pressure_label": "Pressão: {fam} recua (-{n})",
        "strategy_label": "Estratégia: O {k} foi o palco principal hoje.",
        "scale_desc": "Escala: Área proporcional ao volume regional",
        "tactical_title": "INTELIGÊNCIA TÁTICA (24H):",
        "nobling_dynamics": "Dinâmica de Noblagens (24h)",
        "arrow_label": "Seta: Avanço Territorial",
        "circle_label": "Círculo: Consolidação de Área",
        "x_label": "X: Perda de Território"
    },
    "en": {
        "ranking": "Ranking by {label}",
        "tribe": "Tribes",
        "player": "Players",
        "dominance_world": "World Dominance",
        "conquests_24h": "Conquests (24h)",
        "heatmap": "Heatmap: Combat (24h)",
        "war": "Tribe Encounter",
        "update": "Updated",
        "daily": "Updated daily",
        "continent": "By Continent",
        "points": "Points",
        "avg_noblings": "Daily Average Noblings",
        "combat_zones": "Combat Zones",
        "per_day": "villages/day",
        "villages": "villages",
        "pts": "pts",
        "alt_total": "total villages",
        "tactical_analysis": "Tactical Analysis (K)",
        "hot_spot_label": "Hot Spot: Continent {k}",
        "hot_spot_desc": "({n} noblings in the region)",
        "advance_label": "Advance: {fam} in {k}",
        "pressure_label": "Pressure: {fam} receding (-{n})",
        "strategy_label": "Strategy: {k} was today's main stage.",
        "scale_desc": "Scale: Area proportional to regional volume",
        "tactical_title": "TACTICAL INTELLIGENCE (24H):",
        "nobling_dynamics": "Nobling Dynamics (24h)",
        "arrow_label": "Arrow: Territorial Advance",
        "circle_label": "Circle: Area Consolidation",
        "x_label": "X: Territorial Loss"
    }
}

# Local das fontes
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
FONT_ARIAL = os.path.join(FONT_DIR, "arial.ttf")
FONT_ARIAL_BOLD = os.path.join(FONT_DIR, "arialbd.ttf")

def get_font(size, bold=False):
    f_path = FONT_ARIAL_BOLD if bold else FONT_ARIAL
    try:
        return ImageFont.truetype(f_path, size)
    except:
        return ImageFont.load_default()

def get_world_start_date(mundo, domain):
    """Tenta descobrir a data de início do mundo via scraping (Settings)."""
    if mundo in CONFIG.get("server_start_dates", {}):
        return CONFIG["server_start_dates"][mundo]
    
    url = f"https://{mundo}.{domain}/page/settings"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, timeout=10, headers=headers)
        content = resp.text
        
        # 1. Busca ampla pelo valor após 'Data de início', 'Start date' ou 'Startdatum'
        m_raw = re.search(r'>(?:Data de início|Start date|Startdatum)<.*?<td>(.*?)<', content, re.DOTALL | re.IGNORECASE)
        if not m_raw: return None
        date_str = m_raw.group(1).lower()

        # 2. Extrair Números (Dia e Ano)
        m_nums = re.findall(r'\d{1,4}', date_str)
        if len(m_nums) < 2: return None
        
        # 3. Detectar Mês (Nome ou Número)
        day = m_nums[0].zfill(2)
        year = next((n for n in m_nums if len(n)==4), datetime.now().year)
        
        # Mapa de meses (PT, DE, EN)
        months_map = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06', 
            'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
            'okt': '10', 'dec': '12', 'feb': '02', 'apr': '04', 'may': '05', 'aug': '08', 'sep': '09'
        }
        
        month_num = "01"
        # Tenta achar nome de mês
        for name, num in months_map.items():
            if name in date_str:
                month_num = num
                break
        else:
            # Se não achou nome, tenta achar o segundo número como mês
            if len(m_nums) >= 2 and len(m_nums[1]) <= 2:
                month_num = m_nums[1].zfill(2)

        return f"{year}-{month_num}-{day}"
            
    except:
        pass
    return None

def save_config_update(key, world, value):
    """Atualiza o arquivo config.json com novos dados cacheados."""
    global CONFIG
    if key not in CONFIG: CONFIG[key] = {}
    CONFIG[key][world] = value
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=2, ensure_ascii=False)
    except:
        pass

def normalize_tag(tag):
    tag = str(tag).upper().strip()
    tag = tag.replace('!', 'I').replace('1', 'I').replace('3', 'E').replace('4', 'A').replace('0', 'O')
    tag = re.sub(r'[^A-Z0-9]', '', tag)
    m = re.match(r'^([A-Z]+)\d*$', tag)
    if m: tag = m.group(1)
    return tag if tag else str(tag)

def mute_color(color, amount=0.5):
    r, g, b = color
    return (int(r * amount), int(g * amount), int(b * amount))

def draw_arrow(draw, p1, p2, color, width=5, scale=1.0):
    """Seta tática com contorno e escala."""
    x1, y1 = p1; x2, y2 = p2
    w = max(int(width * scale), 3)
    OUTLINE = (0, 0, 0, 255)
    # Linha com borda: desenha uma linha preta mais larga primeiro
    draw.line([p1, p2], fill=OUTLINE, width=w + 2)
    draw.line([p1, p2], fill=color + (255,), width=w)
    angle = np.arctan2(y2 - y1, x2 - x1)
    head_size = int(18 * scale)
    # Ponta da seta com borda
    h1o = (x2 - (head_size+2) * np.cos(angle - np.pi/6), y2 - (head_size+2) * np.sin(angle - np.pi/6))
    h2o = (x2 - (head_size+2) * np.cos(angle + np.pi/6), y2 - (head_size+2) * np.sin(angle + np.pi/6))
    draw.polygon([p2, h1o, h2o], fill=OUTLINE)
    h1c = (x2 - head_size * np.cos(angle - np.pi/6), y2 - head_size * np.sin(angle - np.pi/6))
    h2c = (x2 - head_size * np.cos(angle + np.pi/6), y2 - head_size * np.sin(angle + np.pi/6))
    draw.polygon([p2, h1c, h2c], fill=color + (255,))

def cluster_points(points, max_dist=8):
    if not points: return []
    clusters = []
    for p in points:
        found = False
        for c in clusters:
            dist = np.sqrt((p[0] - c['x'])**2 + (p[1] - c['y'])**2)
            if dist < max_dist:
                c['x'] = (c['x'] * c['count'] + p[0]) / (c['count'] + 1)
                c['y'] = (c['y'] * c['count'] + p[1]) / (c['count'] + 1)
                c['count'] += 1
                found = True
                break
        if not found: clusters.append({'x': p[0], 'y': p[1], 'count': 1})
    return clusters

class TWData:
    def __init__(self, mundo, domain):
        self.mundo = mundo
        self.url_base = f"https://{mundo}.{domain}/map"
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

def generate_map(mundo, server_key, target_root, mode, entity="tribe", metric="points", war_config=None):
    """
    server_key: ".BR", ".NET", etc.
    target_root: "Resultados"
    """
    domain = DOMAINS.get(server_key, "tribalwars.com.br")
    lang = "pt" if server_key in [".BR", ".PT"] else "en"
    txt = TEXTS[lang]
    
    data = TWData(mundo, domain)
    print(f"[{server_key}] [{mundo}] Processando {mode} - {entity} - {metric}")
    
    df_village = data.fetch("village.txt")
    df_player = data.fetch("player.txt")
    df_ally = data.fetch("ally.txt")
    
    if df_village.empty or df_player.empty: 
        print(f"Erro ao baixar dados base do {mundo}")
        return

    # Mapear IDs
    df_player.columns = list(range(df_player.shape[1]))
    df_village.columns = list(range(df_village.shape[1]))
    
    # FIX: Remove aldeias do K00 (bug de admin/outliers) de todos os mapas
    df_village = df_village[~(((df_village[3] // 100) == 0) & ((df_village[2] // 100) == 0))]
    
    if not df_ally.empty:
        df_ally.columns = list(range(df_ally.shape[1]))
    
    # 1. Preparar Entidades e Ranking
    top_entries = []
    map_id_color = {}
    label_metric = metric.upper()
    
    if mode == 'ranking':
        if entity == 'player':
            df_target = df_player.copy()
            metric_map = {"oda": "att", "odd": "def", "ods": "sup"}
            mk = metric_map.get(metric, metric)
            
            if metric == "xgoal":
                start_str = get_world_start_date(mundo, domain)
                if not start_str:
                    print(f"[{mundo}] xGoal abortado: Data de início não encontrada")
                    return
                
                save_config_update("server_start_dates", mundo, start_str)
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                dias = (datetime.now() - start_date).days
                dias = max(dias, 1)
                df_target['val'] = (pd.to_numeric(df_target[3], errors='coerce') - 1) / dias
                label_metric = txt["avg_noblings"]
                sort_cols = ['val', 4]
            elif metric != "points":
                df_kill = data.fetch(f"kill_{mk}.txt")
                if not df_kill.empty:
                    df_kill.columns = list(range(df_kill.shape[1]))
                    df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                    df_target = df_target.merge(df_kill, on=0, how='left')
                
                df_target['val'] = pd.to_numeric(df_target.get('val', 0), errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}"
                # Tie-breaker: Se OD for igual (como 0), ordena por pontos (coluna 4)
                sort_cols = ['val', 4]
            else:
                df_target['val'] = pd.to_numeric(df_target[4], errors='coerce')
                label_metric = txt["points"]
                sort_cols = ['val']
            
            # Filtra apenas quem tem saldo (maior que 0)
            df_target = df_target[df_target['val'] > 0]
            top15 = df_target.sort_values(sort_cols, ascending=False).head(15)
            for i, row in enumerate(top15.itertuples()):
                map_id_color[row[1]] = COLORS[i]
                top_entries.append({'name': row[2], 'val': row.val, 'rank': i+1, 'color': COLORS[i]})
            target_ids_for_map = df_village[df_village[4].isin(map_id_color.keys())].copy()
            target_ids_for_map['color_key'] = target_ids_for_map[4]

        else: # Tribe Ranking
            df_target = df_ally.copy()
            df_target['family'] = df_target[2].apply(normalize_tag)
            df_target['points'] = pd.to_numeric(df_target[6], errors='coerce').fillna(0) # Pontos totais
            
            metric_map = {"oda": "att", "odd": "def", "ods": "sup"}
            mk = metric_map.get(metric, metric)
            
            if metric != "points":
                df_kill = data.fetch(f"kill_{mk}_tribe.txt")
                if not df_kill.empty:
                    df_kill.columns = list(range(df_kill.shape[1]))
                    df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                    df_target = df_target.merge(df_kill, on=0, how='left')
                
                df_target['val'] = pd.to_numeric(df_target.get('val', 0), errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}"
                sort_cols = ['val', 'points']
            else:
                df_target['val'] = df_target['points']
                label_metric = txt["points"]
                sort_cols = ['val']
            
            # Agrupar por família, somando OD e Pontos
            fams = df_target.groupby('family').agg({'val': 'sum', 'points': 'sum'}).reset_index()
            # Filtra apenas quem tem saldo (maior que 0)
            fams = fams[fams['val'] > 0]
            fams = fams.sort_values(sort_cols, ascending=False).head(15)
            
            for i, row in enumerate(fams.itertuples()):
                map_id_color[row.family] = COLORS[i]
                top_entries.append({'name': row.family, 'val': row.val, 'rank': i+1, 'color': COLORS[i]})
            
            df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
            df_v = df_village.merge(df_p, on=4, how='left')
            df_v['family'] = df_v['ally_id'].map(df_target.set_index(0)['family'])
            target_ids_for_map = df_v[df_v['family'].isin(map_id_color.keys())].copy()
            target_ids_for_map['color_key'] = target_ids_for_map['family']

    elif mode == 'dominance_k':
        df_v = df_village.copy()
        df_v['K'] = (df_v[3] // 100) * 10 + (df_v[2] // 100)
        df_v = df_v[df_v[4] != 0]
        
        if entity == 'player':
            counts = df_v.groupby(['K', 4]).size().reset_index(name='c')
            total_k = df_v.groupby('K').size().reset_index(name='total')
            counts = counts.merge(total_k, on='K')
            counts['pct'] = (counts['c'] / counts['total']) * 100
            best_in_k = counts.sort_values(['K', 'pct'], ascending=[True, False]).groupby('K').head(2)
            player_names = df_player.set_index(0)[1].to_dict()
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
        else:
            df_target = df_ally.copy()
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
        label_metric = "Dominancia %"

    elif mode == 'conquests':
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time())
        df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        df_target = df_ally.copy()
        df_target['family'] = df_target[2].apply(normalize_tag)
        map_aid_fam = df_target.set_index(0)['family'].to_dict()
        map_pid_aid = df_player.set_index(0)[2].to_dict()
        df_conq.loc[:, 'new_aid'] = df_conq['new'].map(map_pid_aid)
        df_conq.loc[:, 'fam'] = df_conq['new_aid'].map(map_aid_fam)
        counts = df_conq[df_conq['fam'].notna()].groupby('fam').size().reset_index(name='c').sort_values('c', ascending=False).head(15)
        for i, r in enumerate(counts.itertuples()):
            map_id_color[r.fam] = COLORS[i]
            top_entries.append({'name': r.fam, 'val': r.c, 'rank': i+1, 'color': COLORS[i]})
        label_metric = txt["conquests_24h"]
        df_p = df_player[[0, 2]].rename(columns={0: 4, 2: 'ally_id'})
        df_v = df_village.merge(df_p, on=4, how='left')
        df_v['family'] = df_v['ally_id'].map(map_aid_fam)
        target_ids_for_map = df_v[df_v['family'].isin(map_id_color.keys())].copy()
        target_ids_for_map['color_key'] = target_ids_for_map['family']
        villages_conq = df_village[df_village[0].isin(df_conq['vid'])].merge(df_conq, left_on=0, right_on='vid')
        villages_conq['color'] = villages_conq['fam'].map(map_id_color)
        villages_conq = villages_conq.dropna(subset=['color'])

    elif mode == 'combat_heatmap':
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time())
        df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        villages_conq = df_village[df_village[0].isin(df_conq['vid'])].merge(df_conq, left_on=0, right_on='vid')
        df_p_simple = df_player[[0, 2]].rename(columns={0: 'pid', 2: 'aid'})
        villages_conq = villages_conq.merge(df_p_simple.rename(columns={'pid': 'new', 'aid': 'new_aid'}), on='new', how='left')
        villages_conq = villages_conq.merge(df_p_simple.rename(columns={'pid': 'old', 'aid': 'old_aid'}), on='old', how='left')
        villages_conq['new_aid'] = villages_conq['new_aid'].fillna(0).astype(int)
        villages_conq['old_aid'] = villages_conq['old_aid'].fillna(0).astype(int)
        label_metric = txt["combat_zones"]
        top_entries = []

    elif mode == 'conquest_hotspot':
        df_conq = data.fetch("conquer.txt")
        if df_conq.empty: return
        df_conq.columns = ["vid", "time", "new", "old"]
        agora = int(time.time()); df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
        
        df_target = df_ally.copy()
        df_target['family'] = df_target[2].apply(normalize_tag)
        map_aid_fam = df_target.set_index(0)['family'].to_dict()
        map_pid_aid = df_player.set_index(0)[2].to_dict()
        map_pid_fam = {pid: map_aid_fam.get(aid) for pid, aid in map_pid_aid.items()}
        map_vid_xy = df_village.set_index(0)[[2, 3]].to_dict('index')

        fams = df_target.groupby('family')[4].sum().sort_values(ascending=False).head(15).index.tolist()
        map_fam_color = {f: COLORS[i % len(COLORS)] for i, f in enumerate(fams)}
        for i, f in enumerate(fams):
            top_entries.append({'name': f, 'val': 0, 'rank': i+1, 'color': COLORS[i]})
        
        df_p_top = df_player[df_player[2].map(map_aid_fam).isin(fams)]
        target_ids_for_map = df_village[df_village[4].isin(df_p_top[0])].copy()
        target_ids_for_map['color_key'] = target_ids_for_map[4].map(map_pid_fam)
        label_metric = "Dinâmica de Noblagens"

    # --- DESENHO ARTÍSTICO ---
    box_v = target_ids_for_map if mode not in ['combat_heatmap', 'dominance_k', 'conquest_hotspot'] else df_village
    if box_v.empty: x_min, x_max, y_min, y_max = 0, 999, 0, 999
    else:
        # Pega os limites das aldeias, ignorando (0,0) que costuma ser outlier/admin
        v_clean = box_v[~((box_v[2] == 0) & (box_v[3] == 0))]
        if v_clean.empty: v_clean = box_v # fallback se for a única aldeia
        
        x_min, x_max = int(v_clean[2].min()), int(v_clean[2].max())
        y_min, y_max = int(v_clean[3].min()), int(v_clean[3].max())
        
        # Ajusta para incluir o Continente (K) inteiro
        x_min = (x_min // 100) * 100
        x_max = (x_max // 100) * 100 + 100
        y_min = (y_min // 100) * 100
        y_max = (y_max // 100) * 100 + 100

        # Para mapas globais (Dominância/Hotspot), garante que o centro (500,500) não seja cortado
        # e mantém uma área mínima de visão para dar contexto
        if mode in ['dominance_k', 'conquest_hotspot']:
            x_min = min(x_min, 400)
            x_max = max(x_max, 600)
            y_min = min(y_min, 400)
            y_max = max(y_max, 600)

    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(1000, x_max), min(1000, y_max)
    w_dim, h_dim = x_max - x_min, y_max - y_min
    escala = 1000 / max(w_dim, h_dim, 1)
    off_x, off_y = (1000 - w_dim * escala) / 2, (1000 - h_dim * escala) / 2
    def map_xy(x, y): return int((x - x_min) * escala + off_x), int((y - y_min) * escala + off_y)

    legenda_w = 450 if mode != 'combat_heatmap' else 0
    img = Image.new('RGBA', (1000 + legenda_w, 1000), (93, 113, 27, 255))
    draw = ImageDraw.Draw(img)
    if legenda_w > 0: draw.rectangle([1000, 0, 1000+legenda_w, 1000], fill=(237, 217, 174, 255))
    for b in range(0, 1000, 100):
        mx, _ = map_xy(b, 0); _, my = map_xy(0, b)
        if 0 <= mx <= 1000: draw.line([(mx, 0), (mx, 1000)], fill=(45, 65, 15, 255))
        if 0 <= my <= 1000: draw.line([(0, my), (1000, my)], fill=(45, 65, 15, 255))
    draw.line([(1000, 0), (1000, 1000)], fill=(0,0,0,255), width=2)

    if mode == 'combat_heatmap':
        overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        for r in villages_conq.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            if r.new_aid != 0 and r.old_aid != 0 and r.new_aid != r.old_aid:
                cor, ra, ri, aa, ai = (220, 20, 20), 12, 5, 70, 150
            else: cor, ra, ri, aa, ai = (140, 100, 70), 8, 3, 50, 100
            o_draw.ellipse([x-ra, y-ra, x+ra, y+ra], fill=cor + (aa,))
            o_draw.ellipse([x-ri, y-ri, x+ri, y+ri], fill=cor + (ai,))
        overlay = overlay.filter(ImageFilter.GaussianBlur(6))
        img.paste(overlay, (0,0), overlay)
    elif mode not in ['dominance_k', 'conquest_hotspot']:
        overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            o_draw.ellipse([x-12, y-12, x+12, y+12], fill=tuple(map_id_color[r.color_key]) + (255,))
        overlay = overlay.filter(ImageFilter.GaussianBlur(2))
        alpha = overlay.getchannel('A').point(lambda i: int(i * 0.50))
        overlay.putalpha(alpha)
        img.paste(overlay, (0,0), overlay)
        source_dots = villages_conq if mode == 'conquests' else target_ids_for_map
        for r in source_dots.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = tuple(r.color if mode == 'conquests' else map_id_color[r.color_key])
            draw.ellipse([x-2, y-2, x+3, y+3], fill=cor + (255,), outline=(0,0,0,255))
    elif mode == 'dominance_k': # Dominance K
        f_k_bold, f_k_small = get_font(12, True), get_font(8, False)
        for k_data in draw_data_k:
            kx, ky = k_data['K'] % 10 * 100, k_data['K'] // 10 * 100
            x1, y1 = map_xy(kx, ky); x2, y2 = map_xy(kx+100, ky+100)
            cx = (x1 + x2) // 2
            draw.text((x1+5, y1+5), f"K{k_data['K']}", fill=(0,0,0,120), font=get_font(10))
            ty = y1 + 35
            for best in k_data['best']:
                draw.text((cx, ty), best['name'][:10], fill=tuple(best['color'])+(255,), font=f_k_bold, anchor="mm")
                draw.text((cx, ty+12), f"{best['pct']:.1f}%", fill=tuple(best['color'])+(255,), font=f_k_small, anchor="mm")
                ty += 28
    elif mode == 'conquest_hotspot':
        # Grade Especial e Lógica Tática V7
        f_k = get_font(12, True)
        for bx in range(0, 1000, 100):
            for by in range(0, 1000, 100):
                mx, my = map_xy(bx, by); k = (by // 100) * 10 + (bx // 100)
                if 0 <= mx < 1000 and 0 <= my < 1000: draw.text((mx + 5, my + 5), f"K{k}", fill=(200, 200, 200, 100), font=f_k)
        
        tribe_stats = {f: {"adv": 0, "int": 0, "loss": 0, "adv_k": {}} for f in fams}
        k_activity = {k: 0 for k in range(100)}
        def get_k(x, y): return int((y // 100) * 10 + (x // 100))

        overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0)); o_draw = ImageDraw.Draw(overlay)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4]); fam = r.color_key
            if fam in map_fam_color: o_draw.ellipse([x-12, y-12, x+12, y+12], fill=tuple(map_fam_color[fam]) + (255,))
        # Aplicação de efeito "Cloud" uniforme
        overlay = overlay.filter(ImageFilter.GaussianBlur(2))
        alpha = overlay.getchannel('A').point(lambda i: int(i * 0.50))
        overlay.putalpha(alpha)
        img.paste(overlay, (0,0), overlay)

        for fam in fams:
            color = tuple(map_fam_color[fam])
            v_tribe = target_ids_for_map[target_ids_for_map.color_key == fam]
            if v_tribe.empty: continue
            cx_avg, cy_avg = v_tribe[2].mean(), v_tribe[3].mean()
            avg_r = np.sqrt((v_tribe[2]-cx_avg)**2 + (v_tribe[3]-cy_avg)**2).mean()
            
            adv_p, int_p, loss_p = [], [], []
            c_fam = df_conq[df_conq['new'].map(map_pid_fam) == fam]
            for c in c_fam.itertuples():
                if c.vid not in map_vid_xy: continue
                if map_pid_fam.get(c.new) == map_pid_fam.get(c.old): continue
                cx, cy = map_vid_xy[c.vid][2], map_vid_xy[c.vid][3]
                if np.sqrt((cx-cx_avg)**2 + (cy-cy_avg)**2) > (1.2 * avg_r): adv_p.append((cx, cy))
                else: int_p.append((cx, cy))
            l_fam = df_conq[df_conq['old'].map(map_pid_fam) == fam]
            for l in l_fam.itertuples():
                if l.vid not in map_vid_xy: continue
                if map_pid_fam.get(l.new) == map_pid_fam.get(l.old): continue
                loss_p.append((map_vid_xy[l.vid][2], map_vid_xy[l.vid][3]))

            for cl in cluster_points(adv_p, 10):
                k = get_k(cl['x'], cl['y']); tribe_stats[fam]["adv"] += cl['count']; k_activity[k] += cl['count']
                tribe_stats[fam]["adv_k"][k] = tribe_stats[fam]["adv_k"].get(k, 0) + cl['count']
                coords = v_tribe[[2, 3]].values
                nx, ny = coords[np.argmin(np.sqrt((coords[:,0]-cl['x'])**2 + (coords[:,1]-cl['y'])**2))]
                draw_arrow(draw, map_xy(nx, ny), (map_xy(cl['x'], cl['y'])), color, scale=np.sqrt(cl['count']))
            for cl in cluster_points(int_p, 8):
                k = get_k(cl['x'], cl['y']); tribe_stats[fam]["int"] += cl['count']; k_activity[k] += cl['count']
                mx, my = map_xy(cl['x'], cl['y']); r = int(9 * np.sqrt(cl['count']))
                draw.ellipse([mx-r-1, my-r-1, mx+r+1, my+r+1], fill=(0,0,0,255)) # Borda de 1px
                draw.ellipse([mx-r, my-r, mx+r, my+r], fill=color + (255,))
            for cl in cluster_points(loss_p, 8):
                k = get_k(cl['x'], cl['y']); tribe_stats[fam]["loss"] += cl['count']; k_activity[k] += cl['count']
                mx, my = map_xy(cl['x'], cl['y']); sz = int(12 * np.sqrt(cl['count'])); w = max(int(5 * np.sqrt(cl['count'])), 3)
                # Borda do X
                draw.line([(mx-sz-1, my-sz-1), (mx+sz+1, my+sz+1)], fill=(0,0,0,255), width=w+2)
                draw.line([(mx+sz+1, my-sz-1), (mx-sz-1, my+sz+1)], fill=(0,0,0,255), width=w+2)
                # Centro do X
                draw.line([(mx-sz, my-sz), (mx+sz, my+sz)], fill=color + (255,), width=w)
                draw.line([(mx+sz, my-sz), (mx-sz, my+sz)], fill=color + (255,), width=w)

        # Rodapé e Análise
        draw.rectangle([1015, 730, 1000+legenda_w-15, 935], outline=(0,0,0), width=3)
        draw.text((1025, 740), txt["tactical_title"], fill=(0,0,0), font=get_font(18, True))
        top_k = max(k_activity, key=k_activity.get)
        best_adv_fam = max([f for f in fams if tribe_stats[f]["adv"] > 0] or [fams[0]], key=lambda f: tribe_stats[f]["adv"])
        tk_adv = max(tribe_stats[best_adv_fam]["adv_k"], key=tribe_stats[best_adv_fam]["adv_k"].get) if tribe_stats[best_adv_fam]["adv_k"] else 0
        top_loss_fam = max(tribe_stats, key=lambda f: tribe_stats[f]["loss"])
        y_ln = 780
        draw.text((1025, y_ln), txt["hot_spot_label"].format(k=f"K{top_k}"), fill=(0,0,0), font=get_font(16, True))
        draw.text((1025, y_ln+25), txt["hot_spot_desc"].format(n=k_activity[top_k]), fill=(80,80,80), font=get_font(13))
        draw.text((1025, y_ln+60), f"● {txt['advance_label'].format(fam=best_adv_fam, k=f'K{tk_adv}')}", fill=(0,0,0), font=get_font(15))
        draw.text((1025, y_ln+85), f"● {txt['pressure_label'].format(fam=top_loss_fam, n=tribe_stats[top_loss_fam]['loss'])}", fill=(0,0,0), font=get_font(15))
        draw.text((1025, y_ln+130), txt["strategy_label"].format(k=f"K{top_k}"), fill=(60,60,60), font=get_font(14, True))

    # Legenda Traduzida
    tx, ty = 1015, 25
    draw.text((tx, ty), mundo.upper(), fill=(20,20,20), font=get_font(28, True)); ty += 40
    main_tit = txt["ranking"].format(label=label_metric) if mode == 'ranking' else (txt["nobling_dynamics"] if mode == 'conquest_hotspot' else label_metric)
    draw.text((tx, ty), main_tit, fill=(20,20,20), font=get_font(22, True)); ty += 30
    sub_tit = txt[entity] if mode == 'ranking' else (txt["tactical_analysis"] if mode == 'conquest_hotspot' else txt["continent"])
    if mode == 'conquests' or mode == 'conquest_hotspot': sub_tit = txt["tribe"]
    draw.text((tx, ty), f"Top 15 {sub_tit}", fill=(80,80,80), font=get_font(18, True)); ty += 45
    draw.text((tx, ty), txt["daily"], fill=(120,120,120), font=get_font(14, False)); ty += 25
    draw.line([(tx, ty), (1000+legenda_w-15, ty)], fill=(160,160,160), width=1); ty += 20
    
    for r in top_entries:
        if mode == 'conquest_hotspot':
            # Legenda de Símbolos Simplificada para Hotspot
            draw_arrow(draw, (tx, ty+10), (tx+60, ty+10), (100,100,100), scale=0.8)
            draw.text((tx+75, ty), txt["arrow_label"], fill=(0,0,0), font=get_font(15))
            ty += 35
            draw.ellipse([tx+10, ty+3, tx+40, ty+33], fill=(0,0,0)); draw.ellipse([tx+13, ty+6, tx+37, ty+30], fill=(100,100,100))
            draw.text((tx+75, ty+8), txt["circle_label"], fill=(0,0,0), font=get_font(15))
            ty += 40
            gx, gy = tx+25, ty+15
            draw.line([(gx-10, gy-10), (gx+10, gy+10)], fill=(0,0,0), width=6); draw.line([(gx+10, gy-10), (gx-10, gy+10)], fill=(0,0,0), width=6)
            draw.line([(gx-8, gy-8), (gx+8, gy+8)], fill=(200,0,0), width=4); draw.line([(gx+8, gy-8), (gx-8, gy+8)], fill=(200,0,0), width=4)
            draw.text((tx+75, ty+5), txt["x_label"], fill=(0,0,0), font=get_font(15))
            ty += 45
            for i, r in enumerate(top_entries):
                draw.rectangle([tx, ty, tx+20, ty+20], fill=tuple(r['color'])+(255,))
                draw.text((tx+30, ty), f"{i+1:2d}. {r['name']}", fill=(0,0,0), font=get_font(16, True))
                ty += 28
            break
        
        if metric == "xgoal": val_str = f"{r['val']:.2f} {txt['per_day']}"
        else: val_str = f"{int(r['val']):,}".replace(',', '.')
        if mode == 'dominance_k': val_str = f"{r['val']:.2f}%"
        draw.rectangle([tx, ty+3, tx+16, ty+19], fill=tuple(r['color'])+(255,))
        draw.text((tx + 25, ty), f"{r['rank']}. {r['name']} ({val_str})", fill=(0,0,0), font=get_font(18, True))
        ty += 35

    stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    draw.text((1000+legenda_w-180, 975), f"{txt['update']}: {stamp} UTC", fill=(80,80,80), font=get_font(12))
    
    # Salvar com nova estrutura
    target_path = os.path.join(target_root, server_key, mundo, "Players" if entity == 'player' else "Tribes")
    os.makedirs(target_path, exist_ok=True)
    
    ent = "jogadores" if entity == 'player' else "familias"
    if mode == 'ranking':
        if metric == 'points':
            f_name = f"mapa_top15_{ent}_{mundo}.png"
        else:
            f_name = f"mapa_top15_{metric}_{ent}_{mundo}.png"
    elif mode == 'conquests':
        f_name = f"mapa_top15_conquistas_{mundo}.png"
    elif mode == 'dominance_k':
        if entity == 'player':
            f_name = f"mapa_top15_dominancia_jogadores_K_{mundo}.png"
        else:
            f_name = f"mapa_top15_dominancia_K_{mundo}.png"
    elif mode == 'combat_heatmap':
        f_name = f"mapa_calor_combate_{mundo}.png"
    elif mode == 'conquest_hotspot':
        f_name = f"mapa_conquest_hotspot_{mundo}.png"
    else:
        f_name = f"mapa_{mode}_{mundo}.png"

    img.save(os.path.join(target_path, f_name))
    print(f"Finalizado: {f_name}")

def archive_daily_data(mundo, server_key, target_root):
    """Salva um snapshot JSON dos rankings."""
    domain = DOMAINS.get(server_key, "tribalwars.com.br")
    data = TWData(mundo, domain)
    df_player = data.fetch("player.txt")
    df_ally = data.fetch("ally.txt")
    if df_player.empty: return
    
    # Processar Top 50 Jogadores
    df_player.columns = list(range(df_player.shape[1]))
    players = df_player.sort_values(4, ascending=False).head(50)
    p_data = [{'rank': int(r[5]), 'name': r[1], 'pts': int(r[4]), 'villages': int(r[3])} for r in players.itertuples()]
    
    # Processar Top 50 Tribos
    t_data = []
    if not df_ally.empty:
        df_ally.columns = list(range(df_ally.shape[1]))
        tribes = df_ally.sort_values(4, ascending=False).head(50)
        t_data = [{'rank': int(r[7]), 'name': r[1], 'tag': r[2], 'pts': int(r[4]), 'villages': int(r[6])} for r in tribes.itertuples()]
    
    history_path = os.path.join(target_root, "history", server_key, mundo)
    os.makedirs(history_path, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(history_path, f"{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump({'players': p_data, 'tribes': t_data}, f, indent=2, ensure_ascii=False)
