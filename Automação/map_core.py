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
        "avg_noblings": "Média de Noblagens p/ Dia",
        "combat_zones": "Zonas de Combate",
        "per_day": "aldeias/dia",
        "villages": "aldeias",
        "pts": "pts",
        "alt_total": "total de aldeias"
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
        "alt_total": "total villages"
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
                if start_str:
                    save_config_update("server_start_dates", mundo, start_str)
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    dias = (datetime.now() - start_date).days
                    dias = max(dias, 1)
                    df_target['val'] = (pd.to_numeric(df_target[3], errors='coerce') - 1) / dias
                    label_metric = txt["avg_noblings"]
                else:
                    print(f"[{mundo}] xGoal abortado: Data de início não encontrada")
                    return
            elif metric != "points":
                df_kill = data.fetch(f"kill_{mk}.txt")
                if df_kill.empty: return
                df_kill.columns = [0, 1, 2]
                df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                df_target = df_target.merge(df_kill, on=0, how='left')
                df_target['val'] = pd.to_numeric(df_target['val'], errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}"
            else:
                df_target['val'] = pd.to_numeric(df_target[4], errors='coerce')
                label_metric = txt["points"]
            
            top15 = df_target.sort_values('val', ascending=False).head(15)
            for i, row in enumerate(top15.itertuples()):
                map_id_color[row[1]] = COLORS[i]
                top_entries.append({'name': row[2], 'val': row.val, 'rank': i+1, 'color': COLORS[i]})
            target_ids_for_map = df_village[df_village[4].isin(map_id_color.keys())].copy()
            target_ids_for_map['color_key'] = target_ids_for_map[4]

        else: # Tribe Ranking
            df_target = df_ally.copy()
            df_target['family'] = df_target[2].apply(normalize_tag)
            metric_map = {"oda": "att", "odd": "def"}
            mk = metric_map.get(metric, metric)
            
            if metric != "points":
                df_kill = data.fetch(f"kill_{mk}_tribe.txt")
                if df_kill.empty: return
                df_kill.columns = [0, 1, 2]
                df_kill = df_kill[[1, 2]].rename(columns={1: 0, 2: 'val'})
                df_target = df_target.merge(df_kill, on=0, how='left')
                df_target['val'] = pd.to_numeric(df_target['val'], errors='coerce').fillna(0)
                label_metric = f"OD{metric[2:].upper()}"
            else:
                df_target['val'] = pd.to_numeric(df_target[4], errors='coerce')
                label_metric = txt["alt_total"]
            
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

    # --- DESENHO ARTÍSTICO ---
    box_v = target_ids_for_map if mode not in ['combat_heatmap', 'dominance_k'] else df_village
    if box_v.empty: x_min, x_max, y_min, y_max = 0, 999, 0, 999
    else:
        x_min, x_max = int(box_v[2].min()-30), int(box_v[2].max()+30)
        y_min, y_max = int(box_v[3].min()-30), int(box_v[3].max()+30)
    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(999, x_max), min(999, y_max)
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
    elif mode != 'dominance_k':
        overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        for r in target_ids_for_map.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            o_draw.ellipse([x-10, y-10, x+10, y+10], fill=tuple(map_id_color[r.color_key]) + (255,))
        overlay = overlay.filter(ImageFilter.GaussianBlur(1))
        alpha = overlay.getchannel('A').point(lambda i: int(i * 0.35))
        overlay.putalpha(alpha)
        img.paste(overlay, (0,0), overlay)
        source_dots = villages_conq if mode == 'conquests' else target_ids_for_map
        for r in source_dots.itertuples():
            x, y = map_xy(r[3], r[4])
            if not (0 <= x <= 1000 and 0 <= y <= 1000): continue
            cor = tuple(r.color if mode == 'conquests' else map_id_color[r.color_key])
            draw.ellipse([x-2, y-2, x+3, y+3], fill=cor + (255,), outline=(0,0,0,255))
    else: # Dominance K
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

    # Legenda Traduzida
    tx, ty = 1015, 25
    draw.text((tx, ty), mundo.upper(), fill=(20,20,20), font=get_font(28, True)); ty += 40
    main_tit = txt["ranking"].format(label=label_metric) if mode == 'ranking' else label_metric
    draw.text((tx, ty), main_tit, fill=(20,20,20), font=get_font(22, True)); ty += 30
    sub_tit = txt[entity] if mode == 'ranking' else txt["continent"]
    if mode == 'conquests': sub_tit = txt["tribe"]
    draw.text((tx, ty), f"Top 15 {sub_tit}", fill=(80,80,80), font=get_font(18, True)); ty += 45
    draw.text((tx, ty), txt["daily"], fill=(120,120,120), font=get_font(14, False)); ty += 25
    draw.line([(tx, ty), (1000+legenda_w-15, ty)], fill=(160,160,160), width=1); ty += 20
    
    for r in top_entries:
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
