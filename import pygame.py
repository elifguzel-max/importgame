import pygame
import random
from collections import deque
import heapq
import time

# Pygame Başlatma
pygame.init()

# Grid Ayarları (PDF İsteri: En az 20x50 kare -> 25x50 seçildi)
SATIR = 25
SUTUN = 50
KARE_BOYUT = 22
UST_PANEL = 90

GENISLIK = SUTUN * KARE_BOYUT
YUKSEKLIK = SATIR * KARE_BOYUT + UST_PANEL

ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("YZT Proje 3: Labirentte Yol Bulan Ajan (Hibrit BFS & A*)")

# Renkler
BEYAZ = (245, 245, 245)
SIYAH = (30, 30, 35)        # Duvar
GRI = (210, 210, 215)       # Izgara çizgisi
YESIL = (46, 204, 113)      # Başlangıç
KIRMIZI = (231, 76, 60)     # Hedef
ACIK_MAVI = (133, 193, 233) # Taranan kareler (Animasyon)
SARI = (241, 196, 15)       # Bulunan En Kısa Yol
MOR = (155, 89, 182)        # Hareket Eden Ajan
PANEL_RENK = (25, 32, 45)

font_baslik = pygame.font.SysFont("Arial", 18, bold=True)
font_bilgi = pygame.font.SysFont("Arial", 15)

# Başlangıç ve Hedef Koordinatları
baslangic = (12, 3)
hedef = (12, 46)

# Grid Matrisi (0: Boş, 1: Duvar)
grid = [[0 for _ in range(SUTUN)] for _ in range(SATIR)]

# İstatistikler
istatistik = {
    "BFS": {"bakilan": 0, "yol": 0, "sure": 0.0},
    "A*": {"bakilan": 0, "yol": 0, "sure": 0.0},
    "HIBRIT": {"bakilan": 0, "yol": 0, "yeniden_hesap": 0}
}

def rastgele_engeller_olustur():
    """PDF İsteri: Minimum 8 engelden kaçabileceği rastgele engel blokları oluşturur."""
    global grid
    grid = [[0 for _ in range(SUTUN)] for _ in range(SATIR)]
    engel_sayisi = 18  # Minimum 8 şartını rahatça aşar
    for _ in range(engel_sayisi):
        r = random.randint(1, SATIR - 4)
        c = random.randint(5, SUTUN - 6)
        dikey = random.choice([True, False])
        uzunluk = random.randint(3, 6)
        for i in range(uzunluk):
            nr = r + i if dikey else r
            nc = c if dikey else c + i
            if 0 <= nr < SATIR and 0 <= nc < SUTUN:
                if (nr, nc) != baslangic and (nr, nc) != hedef:
                    grid[nr][nc] = 1

def komsular(dugum):
    r, c = dugum
    yonler = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    sonuc = []
    for dr, dc in yonler:
        nr, nc = r + dr, c + dc
        if 0 <= nr < SATIR and 0 <= nc < SUTUN and grid[nr][nc] == 0:
            sonuc.append((nr, nc))
    return sonuc

def ciz(taranan=set(), yol=[], ajan_konum=None, aktif_mod="Hazir"):
    ekran.fill(BEYAZ)
    
    # Üst Bilgi Paneli
    pygame.draw.rect(ekran, PANEL_RENK, (0, 0, GENISLIK, UST_PANEL))
    
    kontroller = "Sol Tik: Duvar Ekle | Sag Tik: Sil | [R]: Rastgele Engel | [C]: Temizle | [1]: BFS | [2]: A* (Bonus) | [3]: Hibrit Dinamik Ajan"
    yazi1 = font_baslik.render(kontroller, True, (255, 255, 255))
    ekran.blit(yazi1, (15, 10))
    
    karsilastirma = (
        f"Mod: {aktif_mod}   ||   "
        f"BFS -> Bakilan Kare: {istatistik['BFS']['bakilan']} | Yol: {istatistik['BFS']['yol']}   ||   "
        f"A* -> Bakilan Kare: {istatistik['A*']['bakilan']} | Yol: {istatistik['A*']['yol']}"
    )
    yazi2 = font_bilgi.render(karsilastirma, True, (241, 196, 15))
    ekran.blit(yazi2, (15, 42))

    ipucu = "Ipucu: [3] Hibrit modda ajan yururken onune fareyle duvar koyarsaniz dinamik olarak yeni rota cizer!"
    yazi3 = font_bilgi.render(ipucu, True, (170, 210, 230))
    ekran.blit(yazi3, (15, 65))

    # Grid Karelerini Çiz
    for r in range(SATIR):
        for c in range(SUTUN):
            x = c * KARE_BOYUT
            y = r * KARE_BOYUT + UST_PANEL
            rect = (x, y, KARE_BOYUT, KARE_BOYUT)
            
            renk = BEYAZ
            if grid[r][c] == 1:
                renk = SIYAH
            elif (r, c) in yol:
                renk = SARI
            elif (r, c) in taranan:
                renk = ACIK_MAVI
                
            if (r, c) == baslangic:
                renk = YESIL
            elif (r, c) == hedef:
                renk = KIRMIZI
                
            pygame.draw.rect(ekran, renk, rect)
            pygame.draw.rect(ekran, GRI, rect, 1)

    # Dinamik Ajanı Çiz
    if ajan_konum:
        ax = ajan_konum[1] * KARE_BOYUT + KARE_BOYUT // 2
        ay = ajan_konum[0] * KARE_BOYUT + UST_PANEL + KARE_BOYUT // 2
        pygame.draw.circle(ekran, MOR, (ax, ay), KARE_BOYUT // 2 - 2)

    pygame.display.flip()

def yolu_geri_izle(ebeveyn, mevcut):
    yol = []
    while mevcut in ebeveyn:
        yol.append(mevcut)
        mevcut = ebeveyn[mevcut]
    yol.reverse()
    return yol

def bfs_calistir(start_node, animasyon=True):
    """Breadth-First Search (Genişlik Öncelikli Arama)"""
    t0 = time.time()
    kuyruk = deque([start_node])
    ziyaret_edilen = {start_node}
    ebeveyn = {}
    
    while kuyruk:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
                
        mevcut = kuyruk.popleft()
        if mevcut == hedef:
            yol = yolu_geri_izle(ebeveyn, hedef)
            if animasyon:
                istatistik["BFS"]["bakilan"] = len(ziyaret_edilen)
                istatistik["BFS"]["yol"] = len(yol)
                istatistik["BFS"]["sure"] = round((time.time() - t0) * 1000, 1)
                ciz(ziyaret_edilen, yol, aktif_mod="BFS Tamamlandi")
            return yol, ziyaret_edilen

        for komsu in komsular(mevcut):
            if komsu not in ziyaret_edilen:
                ziyaret_edilen.add(komsu)
                ebeveyn[komsu] = mevcut
                kuyruk.append(komsu)
                
        if animasyon and len(ziyaret_edilen) % 4 == 0:
            ciz(ziyaret_edilen, [], aktif_mod="BFS Araniyor...")
            pygame.time.delay(5)
            
    return [], ziyaret_edilen

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_calistir(start_node, animasyon=True):
    """A* (A-Star) Sezgisel En Kısa Yol Algoritması (Bonus)"""
    t0 = time.time()
    acik_kume = []
    heapq.heappush(acik_kume, (0, start_node))
    ebeveyn = {}
    g_skor = {start_node: 0}
    ziyaret_edilen = {start_node}
    
    while acik_kume:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
                
        _, mevcut = heapq.heappop(acik_kume)
        
        if mevcut == hedef:
            yol = yolu_geri_izle(ebeveyn, hedef)
            if animasyon:
                istatistik["A*"]["bakilan"] = len(ziyaret_edilen)
                istatistik["A*"]["yol"] = len(yol)
                istatistik["A*"]["sure"] = round((time.time() - t0) * 1000, 1)
                ciz(ziyaret_edilen, yol, aktif_mod="A* Tamamlandi")
            return yol, ziyaret_edilen

        for komsu in komsular(mevcut):
            gecici_g = g_skor[mevcut] + 1
            if komsu not in g_skor or gecici_g < g_skor[komsu]:
                ebeveyn[komsu] = mevcut
                g_skor[komsu] = gecici_g
                f_skor = gecici_g + manhattan(komsu, hedef)
                heapq.heappush(acik_kume, (f_skor, komsu))
                ziyaret_edilen.add(komsu)
                
        if animasyon and len(ziyaret_edilen) % 2 == 0:
            ciz(ziyaret_edilen, [], aktif_mod="A* Araniyor...")
            pygame.time.delay(8)
            
    return [], ziyaret_edilen

def hibrit_dinamik_ajan():
    """BFS + Dinamik Engel Algılama ve Yeniden Planlama (D-BFS / A* Hibrit)"""
    ajan = baslangic
    yol, taranan = bfs_calistir(ajan, animasyon=False)
    
    if not yol:
        ciz(aktif_mod="HATA: Hedefe Ulasilamiyor!")
        return

    adim_idx = 0
    while ajan != hedef:
        # Ajan hareket ederken kullanıcının fareyle canlı duvar eklemesine izin ver
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
                
        fare_tuslari = pygame.mouse.get_pressed()
        if fare_tuslari[0]: # Sol tık ile canlı engel koyma
            mx, my = pygame.mouse.get_pos()
            if my > UST_PANEL:
                r = (my - UST_PANEL) // KARE_BOYUT
                c = mx // KARE_BOYUT
                if (r, c) != ajan and (r, c) != hedef:
                    grid[r][c] = 1

        # Kalan yolda yeni bir engel oluştu mu kontrol et (Dinamik Planlama)
        kalan_yol = yol[adim_idx:]
        engel_var = any(grid[r][c] == 1 for (r, c) in kalan_yol)
        
        if engel_var:
            # Önüne engel çıktı! Dinamik olarak A* ile hızlı yeniden rota hesapla
            yol, taranan = a_star_calistir(ajan, animasyon=False)
            adim_idx = 0
            if not yol:
                ciz(taranan, [], ajan, aktif_mod="Yol Kapandi! Hedefe Ulasilamiyor.")
                return
        
        ajan = yol[adim_idx]
        adim_idx += 1
        ciz(taranan, yol[adim_idx:], ajan, aktif_mod="Hibrit Dinamik Ajan Ilerliyor...")
        pygame.time.delay(70)

    ciz(taranan, [], hedef, aktif_mod="Hibrit Ajan Hedefe Ulasti!")

# Başlangıçta örnek engellerle aç
rastgele_engeller_olustur()

# Ana Döngü
calisiyor = True
taranan_son = set()
yol_son = []
mod_yazisi = "Hazir"

while calisiyor:
    ciz(taranan_son, yol_son, aktif_mod=mod_yazisi)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            calisiyor = False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                rastgele_engeller_olustur()
                taranan_son, yol_son = set(), []
                mod_yazisi = "Rastgele Engeller Olusturuldu"
            elif event.key == pygame.K_c:
                grid = [[0 for _ in range(SUTUN)] for _ in range(SATIR)]
                taranan_son, yol_son = set(), []
                mod_yazisi = "Harita Temizlendi"
            elif event.key == pygame.K_1:
                yol_son, taranan_son = bfs_calistir(baslangic, animasyon=True)
                mod_yazisi = f"BFS Tamamlandi ({istatistik['BFS']['bakilan']} kare)"
            elif event.key == pygame.K_2:
                yol_son, taranan_son = a_star_calistir(baslangic, animasyon=True)
                mod_yazisi = f"A* Tamamlandi ({istatistik['A*']['bakilan']} kare)"
            elif event.key == pygame.K_3:
                hibrit_dinamik_ajan()
                taranan_son, yol_son = set(), []
                mod_yazisi = "Hibrit Ajan Tamamlandi"

    # Fare ile duvar çizme / silme
    fare = pygame.mouse.get_pressed()
    if fare[0] or fare[2]:
        mx, my = pygame.mouse.get_pos()
        if my > UST_PANEL:
            r = (my - UST_PANEL) // KARE_BOYUT
            c = mx // KARE_BOYUT
            if 0 <= r < SATIR and 0 <= c < SUTUN:
                if (r, c) != baslangic and (r, c) != hedef:
                    grid[r][c] = 1 if fare[0] else 0

pygame.quit()
