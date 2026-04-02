
import os
import pandas as pd
import numpy as np
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from map_core import TWData, DOMAINS, COLORS, TEXTS, get_font, normalize_tag

def draw_arrow(draw, p1, p2, color, width=5, scale=1.0):
    x1, y1 = p1; x2, y2 = p2
    w = max(int(width * scale), 3)
    draw.line([p1, p2], fill=(0, 0, 0, 255), width=w+3)
    draw.line([p1, p2], fill=color + (255,), width=w)
    angle = np.arctan2(y2 - y1, x2 - x1)
    head_size = int(18 * scale)
    h1 = (x2 - (head_size+3) * np.cos(angle - np.pi/6), y2 - (head_size+3) * np.sin(angle - np.pi/6))
    h2 = (x2 - (head_size+3) * np.cos(angle + np.pi/6), y2 - (head_size+3) * np.sin(angle + np.pi/6))
    draw.polygon([p2, h1, h2], fill=(0,0,0,255))
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

def test_conquest_analysis(mundo="br140"):
    domain = DOMAINS[".BR"]; data = TWData(mundo, domain)
    print(f"Buscando dados para {mundo} (V7: TÁTICA)...")
    df_village = data.fetch("village.txt"); df_player = data.fetch("player.txt")
    df_ally = data.fetch("ally.txt"); df_conq = data.fetch("conquer.txt")
    
    if df_village.empty or df_player.empty or df_conq.empty: return
    df_village.columns = list(range(df_village.shape[1])); df_player.columns = list(range(df_player.shape[1]))
    df_ally.columns = list(range(df_ally.shape[1])); df_conq.columns = ["vid", "time", "new_p", "old_p"]
    
    df_ally['family'] = df_ally[2].apply(normalize_tag)
    map_aid_fam = df_ally.set_index(0)['family'].to_dict()
    map_pid_aid = df_player.set_index(0)[2].to_dict()
    map_pid_fam = {pid: map_aid_fam.get(aid) for pid, aid in map_pid_aid.items()}
    
    fams = df_ally.groupby('family')[5].sum().sort_values(ascending=False).head(15).index.tolist()
    map_fam_color = {f: COLORS[i % len(COLORS)] for i, f in enumerate(fams)}
    
    agora = int(time.time()); df_conq = df_conq[df_conq["time"] > (agora - 86400)].copy()
    map_vid_xy = df_village.set_index(0)[[2, 3]].to_dict('index')
    
    df_p_top = df_player[df_player[2].map(map_aid_fam).isin(fams)]
    df_v_top = df_village[df_village[4].isin(df_p_top[0])]
    x_min, x_max = int(df_v_top[2].min()-30), int(df_v_top[2].max()+30)
    y_min, y_max = int(df_v_top[3].min()-30), int(df_v_top[3].max()+30)
    x_min, y_min = max(0, x_min), max(0, y_min); x_max, y_max = min(999, x_max), min(999, y_max)
    
    escala = 1000 / max(x_max - x_min, y_max - y_min, 1)
    off_x = (1000 - (x_max - x_min) * escala) / 2; off_y = (1000 - (y_max - y_min) * escala) / 2
    def map_xy(x, y): return int((x - x_min) * escala + off_x), int((y - y_min) * escala + off_y)
    def get_k(x, y): return int((y // 100) * 10 + (x // 100))

    img = Image.new('RGBA', (1450, 1000), (93, 113, 27, 255)); draw = ImageDraw.Draw(img)
    
    f_k = get_font(12, True)
    for b in range(0, 1001, 100):
        mx, my = map_xy(b, b)
        if 0 <= mx <= 1000: draw.line([(mx, 0), (mx, 1000)], fill=(45, 65, 15, 255), width=1)
        if 0 <= my <= 1000: draw.line([(0, my), (1000, my)], fill=(45, 65, 15, 255), width=1)
    for bx in range(0, 1000, 100):
        for by in range(0, 1000, 100):
            mx, my = map_xy(bx, by); k = (by // 100) * 10 + (bx // 100)
            if 0 <= mx < 1000 and 0 <= my < 1000: draw.text((mx + 5, my + 5), f"K{k}", fill=(200, 200, 200, 100), font=f_k)
    
    overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0)); o_draw = ImageDraw.Draw(overlay)
    for r in df_v_top.itertuples():
        x, y = map_xy(r[3], r[4]); fam = map_pid_fam.get(r[5])
        if fam in map_fam_color: o_draw.ellipse([x-8, y-8, x+8, y+8], fill=tuple(map_fam_color[fam]) + (150,))
    img.paste(overlay, (0,0), overlay.filter(ImageFilter.GaussianBlur(1)))

    tribe_stats = {f: {"adv": 0, "int": 0, "loss": 0, "adv_k": {}} for f in fams}
    k_activity = {k: 0 for k in range(100)}

    for fam in fams:
        color = tuple(map_fam_color[fam])
        v_tribe = df_v_top[df_v_top[4].map(map_pid_fam) == fam]
        if v_tribe.empty: continue
        cx_avg, cy_avg = v_tribe[2].mean(), v_tribe[3].mean()
        avg_r = np.sqrt((v_tribe[2]-cx_avg)**2 + (v_tribe[3]-cy_avg)**2).mean()
        
        adv_p, int_p, loss_p = [], [], []
        c_fam = df_conq[df_conq['new_p'].map(map_pid_fam) == fam]
        for c in c_fam.itertuples():
            if c.vid not in map_vid_xy: continue
            if map_pid_fam.get(c.new_p) == map_pid_fam.get(c.old_p): continue
            cx, cy = map_vid_xy[c.vid][2], map_vid_xy[c.vid][3]
            if np.sqrt((cx-cx_avg)**2 + (cy-cy_avg)**2) > (1.2 * avg_r): adv_p.append((cx, cy))
            else: int_p.append((cx, cy))
        l_fam = df_conq[df_conq['old_p'].map(map_pid_fam) == fam]
        for l in l_fam.itertuples():
            if l.vid not in map_vid_xy: continue
            if map_pid_fam.get(l.new_p) == map_pid_fam.get(l.old_p): continue
            loss_p.append((map_vid_xy[l.vid][2], map_vid_xy[l.vid][3]))

        for cl in cluster_points(adv_p, 8):
            k = get_k(cl['x'], cl['y']); tribe_stats[fam]["adv"] += cl['count']; k_activity[k] += cl['count']
            tribe_stats[fam]["adv_k"][k] = tribe_stats[fam]["adv_k"].get(k, 0) + cl['count']
            coords = v_tribe[[2, 3]].values
            nx, ny = coords[np.argmin(np.sqrt((coords[:,0]-cl['x'])**2 + (coords[:,1]-cl['y'])**2))]
            draw_arrow(draw, map_xy(nx, ny), (map_xy(cl['x'], cl['y'])), color, scale=np.sqrt(cl['count']))
        for cl in cluster_points(int_p, 6):
            k = get_k(cl['x'], cl['y']); tribe_stats[fam]["int"] += cl['count']; k_activity[k] += cl['count']
            mx, my = map_xy(cl['x'], cl['y']); r = int(9 * np.sqrt(cl['count']))
            draw.ellipse([mx-r-2, my-r-2, mx+r+2, my+r+2], fill=(0,0,0,255)); draw.ellipse([mx-r, my-r, mx+r, my+r], fill=color + (255,))
        for cl in cluster_points(loss_p, 7):
            k = get_k(cl['x'], cl['y']); tribe_stats[fam]["loss"] += cl['count']; k_activity[k] += cl['count']
            mx, my = map_xy(cl['x'], cl['y']); sz = int(12 * np.sqrt(cl['count'])); w = max(int(5 * np.sqrt(cl['count'])), 3)
            draw.line([(mx-sz-2, my-sz-2), (mx+sz+2, my+sz+2)], fill=(0,0,0,255), width=w+2)
            draw.line([(mx+sz+2, my-sz-2), (mx-sz-2, my+sz+2)], fill=(0,0,0,255), width=w+2)
            draw.line([(mx-sz, my-sz), (mx+sz, my+sz)], fill=color + (255,), width=w)
            draw.line([(mx+sz, my-sz), (mx-sz, my+sz)], fill=color + (255,), width=w)

    leg_x = 1015; draw.rectangle([1000, 0, 1450, 1000], fill=(237, 217, 174, 255)); draw.line([(1000, 0), (1000, 1000)], fill=(0,0,0,255), width=2)
    draw.text((leg_x, 30), f"{mundo.upper()}", fill=(0,0,0), font=get_font(32, True))
    draw.text((leg_x, 70), "Dinâmica de Noblagens (24h)", fill=(0,0,0), font=get_font(18, True))
    draw.text((leg_x, 95), "TOP 15 Tribos (Rank por Pontos)", fill=(80,80,80), font=get_font(15))
    
    draw_arrow(draw, (leg_x, 150), (leg_x+60, 150), (100,100,100), scale=0.8)
    draw.text((leg_x+75, 140), "Seta: Avanço Territorial", fill=(0,0,0), font=get_font(14))
    draw.ellipse([leg_x+15, 185, leg_x+45, 215], fill=(0,0,0)); draw.ellipse([leg_x+18, 188, leg_x+42, 212], fill=(100,100,100))
    draw.text((leg_x+75, 190), "Círculo: Noblagem Interna", fill=(0,0,0), font=get_font(14))
    gx, gy = leg_x+30, 245
    draw.line([(gx-10, gy-10), (gx+10, gy+10)], fill=(0,0,0), width=5); draw.line([(gx+10, gy-10), (gx-10, gy+10)], fill=(0,0,0), width=5)
    draw.line([(gx-8, gy-8), (gx+8, gy+8)], fill=(200,0,0), width=3); draw.line([(gx+8, gy-8), (gx-8, gy+8)], fill=(200,0,0), width=3)
    draw.text((leg_x+75, 240), "X: Perda de Território", fill=(0,0,0), font=get_font(14))

    ty = 290
    for i, fam in enumerate(fams):
        draw.rectangle([leg_x, ty, leg_x+20, ty+20], fill=tuple(map_fam_color[fam]) + (255,))
        draw.text((leg_x+30, ty), f"{i+1:2d}. {fam}", fill=(0,0,0), font=get_font(16, True)); ty += 28

    # BOX ANALÍTICA TÁTICA
    draw.rectangle([1015, 730, 1435, 935], outline=(0,0,0), width=3)
    draw.text((1025, 740), "INTELIGÊNCIA TÁTICA (24H):", fill=(0,0,0), font=get_font(18, True))
    
    top_k = max(k_activity, key=k_activity.get)
    best_adv_fam = max([f for f in fams if tribe_stats[f]["adv"] > 0] or [fams[0]], key=lambda f: tribe_stats[f]["adv"])
    tk_adv = max(tribe_stats[best_adv_fam]["adv_k"], key=tribe_stats[best_adv_fam]["adv_k"].get) if tribe_stats[best_adv_fam]["adv_k"] else 0
    top_loss_fam = max(tribe_stats, key=lambda f: tribe_stats[f]["loss"])
    
    y_ln = 780
    draw.text((1025, y_ln), f"● Ponto Quente: Continente K{top_k}", fill=(0,0,0), font=get_font(16, True))
    draw.text((1025, y_ln+25), f"  ({k_activity[top_k]} noblagens registradas na região)", fill=(80,80,80), font=get_font(13))
    
    draw.text((1025, y_ln+60), f"● Avanço: {best_adv_fam} ganha terreno no K{tk_adv}", fill=(0,0,0), font=get_font(15))
    draw.text((1025, y_ln+85), f"● Pressão: {top_loss_fam} sob recuo (-{tribe_stats[top_loss_fam]['loss']} aldeias)", fill=(0,0,0), font=get_font(15))
    draw.text((1025, y_ln+130), f"Estratégia: O K{top_k} foi o palco principal hoje.", fill=(60,60,60), font=get_font(14, True))

    nm = datetime.now().strftime("%d/%m/%Y %H:%M")
    draw.text((1015, 950), "Escala: Área proporcional ao volume regional", fill=(100,100,100), font=get_font(12))
    draw.text((1015, 970), f"Gerado em: {nm}", fill=(100,100,100), font=get_font(12))

    os.makedirs("Laboratorio", exist_ok=True)
    img.save("Laboratorio/teste_conquistas_analise_br140.png")
    print("Sucesso V7 Tática!")

if __name__ == "__main__":
    test_conquest_analysis()
