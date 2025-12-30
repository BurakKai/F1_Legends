import streamlit as st
import random
import pandas as pd
import os
import plotly.graph_objects as go # Radar grafiği için gerekli

# ====================================================================
# --- I. SINIF TANIMLARI ---
# ====================================================================

VETERANS_LIST = ["Kayra", "Ahmet", "Yağız", "Kaan"] 

# TARİHİ PİSTLER VE LAKAPLARI
HISTORIC_TRACK_TITLES = {
    "Spa-Francorchamps": "🌧️ Yağmurlu Düzlüklerin Kralı",
    "Silverstone": "🇬🇧 Tarihi Pistin Sahibi",
    "Interlagos": "🇧🇷 Son Yağmur Bükücü",
    "Monaco": "💎 Sürüş Dehası",
    "Monza": "🚀 Hız Tapınağının Ustası"
}

# TRANSFER HAVUZU
INITIAL_ROOKIE_POOL = [
    ("Yavuz", 6, 5, 6, 5), ("Furkan", 5, 5, 5, 5), ("Enes", 6, 4, 5, 5),
    ("Deniz", 4, 5, 4, 6), ("Eren", 5, 5, 4, 6), ("Ayberk", 6, 6, 6, 7),
    ("Kerem", 4, 4, 5, 3)
]

class Driver:
    def __init__(self, name, team, speed, handling, braking, intelligence):
        self.name = name          
        self.team = team          
        
        self.speed = float(speed)
        self.handling = float(handling)  
        self.braking = float(braking)    
        self.intelligence = float(intelligence)
        
        self.category = "Veteran" if name in VETERANS_LIST else "Rookie"
        self.update_overall()
        
        # --- KARİYER SAYAÇLARI ---
        self.seasons_raced = 0
        self.bad_seasons_streak = 0 
        
        # Emeklilik Zamanı
        if self.name == "Barış":
            self.retirement_deadline = 7 # Barış Kuralı
        elif self.category == "Veteran":
            self.retirement_deadline = random.randint(5, 8) 
        else:
            self.retirement_deadline = random.randint(9, 11)

        # --- SEZONLUK İSTATİSTİKLER ---
        self.season_points = 0    
        self.wins = 0           
        self.poles = 0          
        self.podiums = 0        
        self.dnfs = 0           
        
        # --- KARİYER İSTATİSTİKLERİ ---
        self.career_races = 0
        self.career_wins = 0
        self.career_poles = 0
        self.career_podiums = 0
        self.career_dnfs = 0
        self.career_titles = 0
        self.achievements = [] 
        
        # Tarihi pist kazanımları
        self.specific_race_wins = {} 

    def update_overall(self):
        self.overall_power = self.speed + self.handling + self.braking + self.intelligence

    def __repr__(self): return self.name
    def add_points(self, points): self.season_points += points

    def reset_stats_for_new_season(self):
        self.season_points = 0
        self.wins = 0
        self.poles = 0
        self.podiums = 0
        self.dnfs = 0
        self.seasons_raced += 1

    def apply_season_development(self):
        """Gelişim ve Yaşlanma Mantığı"""
        changes = []
        attributes = ["speed", "handling", "braking", "intelligence"]
        attr_names = {"speed": "Hız", "handling": "Kontrol", "braking": "Fren", "intelligence": "Zeka"}
        
        if self.category == "Rookie":
            targets = random.sample(attributes, 2)
            for attr in targets:
                boost = random.uniform(0.3, 0.8)
                current_val = getattr(self, attr)
                if current_val + boost > 10.5: boost = 10.5 - current_val
                setattr(self, attr, current_val + boost)
                changes.append(f"{attr_names[attr]} +{boost:.1f}")
        else:
            roll = random.random()
            target = random.choice(attributes)
            current_val = getattr(self, target)
            
            if roll < 0.35: # Düşüş
                drop = random.uniform(0.1, 0.3)
                if current_val - drop < 4.0: drop = 0 
                setattr(self, target, current_val - drop)
                changes.append(f"{attr_names[target]} -{drop:.1f}")
            elif roll > 0.85: # Tecrübe Artışı
                boost = random.uniform(0.1, 0.2)
                if current_val + boost > 10.5: boost = 0
                setattr(self, target, current_val + boost)
                changes.append(f"{attr_names[target]} +{boost:.1f}")
            else:
                changes.append("Değişim Yok")

        self.update_overall()
        return ", ".join(changes)

class Team:
    def __init__(self, name):
        self.name = name          
        self.drivers = []         
        self.season_points = 0    

    def add_driver(self, driver): self.drivers.append(driver)
    
    def remove_driver(self, driver_name):
        self.drivers = [d for d in self.drivers if d.name != driver_name]

    def calculate_team_points(self):
        self.season_points = sum(d.season_points for d in self.drivers)
    
    def reset_stats(self): self.season_points = 0

class Circuit:
    def __init__(self, name, focus_factor=1.0):
        self.name = name                 
        self.focus_factor = focus_factor 

# ====================================================================
# --- II. SABİT DEĞERLER ---
# ====================================================================

RACE_POINTS = { 1: 15, 2: 12, 3: 10, 4: 8, 5: 6, 6: 4, 7: 3, 8: 2, 9: 1, 10: 0 }
RAIN_CHANCE = 0.20        
RAIN_MULTIPLIER = 1.25    
MAX_POWER = 42.0 
BASE_DNF_CHANCE = 0.01    
POWER_INFLUENCE = 0.30    
CIRCUIT_DNF_INFLUENCE = 0.20 
MASTERY_BOOST = 3.0 
POLE_BOOST = 5.0 
QUALY_POWER_MULTIPLIER = 0.9 
QUALY_CHAOS_BASE = 5.0 
RACE_CHAOS_BASE = 12.0 

CIRCUIT_MASTERY = {
    "Ahmet": ["Spa-Francorchamps", "Singapore", "Suzuka"],
    "Kayra": ["Silverstone", "İstanbul Park", "Interlagos"],
    "Barış": ["Australia"],
    "Kaan": ["Azerbaijan"],
    "Yağız": ["Miami"]
}

# ====================================================================
# --- III. YARDIMCI FONKSİYONLAR ---
# ====================================================================

def generate_driver_comments(drivers, power_rank_map):
    current_standings = sorted(drivers, key=lambda d: d.season_points, reverse=True)
    comments = []
    for i, driver in enumerate(current_standings, 1):
        current_rank = i
        initial_power_rank = power_rank_map.get(driver.name, 5)
        if current_rank < initial_power_rank:
            diff = initial_power_rank - current_rank
            positive_comments = [
                f"🔥 Harika bir sezon geçiriyorum! {diff} sıra yukarıdayım.",
                "🚀 Takım harikalar yaratıyor, şampiyonluk bizim!",
                "🌪️ Performansımdan çok memnunum.",
                "✨ Herkesi şaşırttık, daha yeni başlıyoruz!",
                "📈 Beklentilerin üzerindeyiz.",
                "⭐ Pistte her şey lehimize işliyor.",
                "💪 Baskı yok, sadece gazlıyoruz.",
                "🎯 Podyumlar gelmeye devam edecek."
            ]
            msg = random.choice(positive_comments)
            comments.append((driver.name, msg, "positive"))
        elif current_rank > initial_power_rank:
            negative_comments = [
                f"🥶 Hayal kırıklığı. {diff} sıra gerideyiz.",
                "🔧 Arabada sorunlar var.",
                "⛈️ Şanssızlık peşimi bırakmıyor.",
                "🐢 Daha çok çalışmalıyız.",
                "💥 DNF'ler bizi bitirdi.",
                "📉 İstikrar yakalayamadık.",
                "🚧 Strateji hataları yaptık.",
                "🤕 Araca güvenemiyorum.",
                "❓ Kafam karışık, toparlanmam lazım."
            ]
            msg = random.choice(negative_comments)
            comments.append((driver.name, msg, "negative"))
        else:
            neutral_comments = [
                "👍 Tam beklenen sıradayız.",
                "⚖️ Güç dengesi normal.",
                "🎯 Puan topluyoruz.",
                "😴 Hata yapmamaya çalışıyoruz.",
                "☯️ Dengeli bir sezon."
            ]
            msg = random.choice(neutral_comments)
            comments.append((driver.name, msg, "neutral"))
    return comments

# ====================================================================
# --- IV. TRANSFER, ÖDÜLLER VE SEZON MANTIĞI ---
# ====================================================================

def process_rookie_entry(target_team_name):
    if st.session_state.rookie_pool:
        new_data = st.session_state.rookie_pool.pop(0) 
        r_name, r_s, r_h, r_b, r_i = new_data
        return Driver(r_name, target_team_name, r_s, r_h, r_b, r_i)
    else:
        rand_name = f"Genç_{random.randint(100,999)}"
        return Driver(rand_name, target_team_name, 5, 5, 5, 5)

def distribute_season_awards(drivers, year):
    if not drivers: return
    champion = sorted(drivers, key=lambda d: d.season_points, reverse=True)[0]
    champion.achievements.append(f"🏆 {year} Dünya Şampiyonu")
    champion.career_titles += 1
    max_wins = max(d.wins for d in drivers)
    for d in drivers:
        if d.wins == max_wins and max_wins > 0:
            d.achievements.append(f"🏁 {year} En Çok Galibiyet ({max_wins})")
    max_poles = max(d.poles for d in drivers)
    for d in drivers:
        if d.poles == max_poles and max_poles > 0:
            d.achievements.append(f"⚡ {year} Pole Kralı ({max_poles})")
    max_podiums = max(d.podiums for d in drivers)
    for d in drivers:
        if d.podiums == max_podiums and max_podiums > 0:
            d.achievements.append(f"🍾 {year} Podyum Canavarı ({max_podiums})")
    min_dnfs = min(d.dnfs for d in drivers)
    for d in drivers:
        if d.dnfs == min_dnfs:
            d.achievements.append(f"🛡️ {year} Safe Driver (En Az Kaza)")
    best_gain = -99
    risers = []
    for d in drivers:
        current_rank = sorted(drivers, key=lambda x: x.season_points, reverse=True).index(d) + 1
        gain = st.session_state.power_rank_map.get(d.name, 5) - current_rank
        if gain > best_gain:
            best_gain = gain
            risers = [d]
        elif gain == best_gain:
            risers.append(d)
    if best_gain > 0:
        for d in risers:
            d.achievements.append(f"🚀 {year} Yılın Yükseleni (+{best_gain} Sıra)")

def start_new_season_logic():
    distribute_season_awards(st.session_state.drivers, st.session_state.current_year)
    champion = sorted(st.session_state.drivers, key=lambda d: d.season_points, reverse=True)[0]
    st.session_state.hall_of_fame.append({
        "Yıl": st.session_state.current_year,
        "Şampiyon": champion.name,
        "Takım": champion.team,
        "Puan": champion.season_points
    })
    
    dev_log = []
    for d in st.session_state.drivers:
        change_str = d.apply_season_development()
        dev_log.append({"Pilot": d.name, "Kategori": d.category, "Gelişim": change_str, "Yeni Güç": f"{d.overall_power:.1f}"})
    st.session_state.development_history = dev_log

    transfer_news = []
    drivers_to_remove = []
    sorted_drivers = sorted(st.session_state.drivers, key=lambda d: d.season_points, reverse=True)
    
    for d in st.session_state.drivers:
        if d.seasons_raced >= d.retirement_deadline:
            transfer_news.append(f"👋 **EMEKLİLİK:** {d.seasons_raced} sezonun ardından **{d.name}** ({d.team}) emekliye ayrıldı.")
            drivers_to_remove.append((d, "retired"))

    bottom_3 = sorted_drivers[-3:]
    for i, d in enumerate(bottom_3):
        if any(rem[0].name == d.name for rem in drivers_to_remove): continue
        should_fire = False
        reason = ""
        my_idx = sorted_drivers.index(d)
        if my_idx > 0:
            driver_ahead = sorted_drivers[my_idx - 1]
            gap = driver_ahead.season_points - d.season_points
            if gap >= 25:
                d.bad_seasons_streak += 1
                reason = f"Puan farkı çok açıldı ({gap} puan)."
        initial_rank = st.session_state.power_rank_map.get(d.name, 5)
        current_rank = my_idx + 1
        if current_rank >= initial_rank + 3: 
             d.bad_seasons_streak += 1
             reason = f"Beklenti {initial_rank}, Gerçekleşen {current_rank}."
        if d.season_points == 0 and current_rank == 10: d.bad_seasons_streak += 2
        
        if d.bad_seasons_streak >= 2: should_fire = True
            
        if should_fire:
            transfer_news.append(f"📢 **KOVULMA:** **{d.name}** ({d.team}), başarısız performans nedeniyle gönderildi. ({reason})")
            drivers_to_remove.append((d, "fired"))
            st.session_state.rookie_pool.append((d.name, d.speed, d.handling, d.braking, d.intelligence))

    for old_driver, status in drivers_to_remove:
        st.session_state.retired_drivers.append(old_driver)
        if old_driver in st.session_state.drivers:
            st.session_state.drivers.remove(old_driver)
        target_team_name = old_driver.team
        for team in st.session_state.teams:
            if team.name == target_team_name:
                team.remove_driver(old_driver.name)
                new_driver = process_rookie_entry(target_team_name)
                team.add_driver(new_driver)
                st.session_state.drivers.append(new_driver)
                if status == "retired":
                    transfer_news.append(f"🆕 **İMZA:** {target_team_name}, **{new_driver.name}** ile sözleşme imzaladı.")
                else:
                    transfer_news.append(f"🔄 **TRANSFER:** {target_team_name}, **{new_driver.name}**'i getirdi.")

    st.session_state.transfer_log = transfer_news
    st.session_state.current_year += 1
    st.session_state.current_race_idx = 0
    st.session_state.race_history = []
    st.session_state.all_winners = []
    st.session_state.all_poles = []
    
    st.session_state.points_history = {d.name: [0] for d in st.session_state.drivers}
    
    for d in st.session_state.drivers:
        d.reset_stats_for_new_season()
    for t in st.session_state.teams: t.reset_stats()
        
    power_sorted = sorted(st.session_state.drivers, key=lambda d: d.overall_power, reverse=True)
    st.session_state.power_rank_map = {d.name: i+1 for i, d in enumerate(power_sorted)}
    random.shuffle(st.session_state.circuits)

# ====================================================================
# --- V. YARIŞ MANTIĞI ---
# ====================================================================

def simulate_race_logic(drivers, circuit):
    log_messages = [] 
    chaos_range_qualy = QUALY_CHAOS_BASE * circuit.focus_factor
    qualifying_performances = []
    for driver in drivers:
        dynamic_power = driver.overall_power 
        if driver.name in CIRCUIT_MASTERY and circuit.name in CIRCUIT_MASTERY[driver.name]:
            dynamic_power += MASTERY_BOOST
        weighted_power = dynamic_power * QUALY_POWER_MULTIPLIER
        random_factor = random.uniform(-chaos_range_qualy, chaos_range_qualy)
        qualifying_performances.append((driver, weighted_power + random_factor))
        
    final_ranking_qualy = sorted(qualifying_performances, key=lambda x: x[1], reverse=True)
    pole_sitter = final_ranking_qualy[0][0]
    pole_sitter.poles += 1
    pole_sitter.career_poles += 1 
    
    is_rainy = random.random() < RAIN_CHANCE
    weather = "Yağmurlu 🌧️" if is_rainy else "Kuru ☀️"
    log_messages.append(f"Hava: {weather} | Pole: **{pole_sitter.name}**")
    
    chaos_range_race = RACE_CHAOS_BASE * circuit.focus_factor
    race_performances = []
    dnf_drivers = []
    
    for driver in drivers:
        driver.career_races += 1
        handling = driver.handling * RAIN_MULTIPLIER if is_rainy else driver.handling
        intel = driver.intelligence * RAIN_MULTIPLIER if is_rainy else driver.intelligence
        boost = MASTERY_BOOST if (driver.name in CIRCUIT_MASTERY and circuit.name in CIRCUIT_MASTERY[driver.name]) else 0.0
        power = driver.speed + handling + driver.braking + intel + boost
        if driver == pole_sitter: power += POLE_BOOST
        dnf_chance = BASE_DNF_CHANCE + ((1 - (driver.overall_power / MAX_POWER)) * POWER_INFLUENCE) + ((circuit.focus_factor - 1.0) * CIRCUIT_DNF_INFLUENCE)
        
        if random.random() < dnf_chance:
            dnf_drivers.append(driver)
            driver.dnfs += 1
            driver.career_dnfs += 1
            log_messages.append(f"❌ **DNF:** {driver.name} kaza yaptı!")
        else:
            score = power + random.uniform(-chaos_range_race, chaos_range_race)
            race_performances.append((driver, score))
            
    final_ranking = sorted(race_performances, key=lambda x: x[1], reverse=True)
    winner = final_ranking[0][0] if final_ranking else None
    
    if winner: 
        winner.career_wins += 1 
        if circuit.name in HISTORIC_TRACK_TITLES:
            if circuit.name in winner.specific_race_wins:
                winner.specific_race_wins[circuit.name] += 1
            else:
                winner.specific_race_wins[circuit.name] = 1
    
    race_data = []
    podium_drivers = final_ranking[:10]
    for rank, (driver, score) in enumerate(podium_drivers, 1):
        if rank == 1: driver.wins += 1
        if rank <= 3: 
            driver.podiums += 1
            driver.career_podiums += 1
        pts = RACE_POINTS.get(rank, 0)
        driver.add_points(pts)
        race_data.append({"Sıra": rank, "Pilot": driver.name, "Takım": driver.team, "Puan": f"+{pts}", "Durum": "Tamamladı"})
        
    for rank, (driver, score) in enumerate(final_ranking[10:], 11):
        race_data.append({"Sıra": rank, "Pilot": driver.name, "Takım": driver.team, "Puan": "0", "Durum": "Tamamladı"})
    for driver in dnf_drivers:
        race_data.append({"Sıra": "-", "Pilot": driver.name, "Takım": driver.team, "Puan": "0", "Durum": "DNF"})
        
    qual_data_simple = [{"Sıra": i+1, "Pilot": d.name, "Skor": f"{s:.1f}"} for i, (d, s) in enumerate(final_ranking_qualy)]
    
    return log_messages, race_data, qual_data_simple, winner, pole_sitter

# ====================================================================
# --- VI. STREAMLIT UYGULAMASI ---
# ====================================================================

st.set_page_config(page_title="F1 Ultimate Simulator", layout="wide", page_icon="🏎️")

st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .metric-container { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .winner-box { border: 2px solid gold; border-radius: 15px; padding: 10px; text-align: center; background-color: #fff8dc; }
    .champion-banner { background: linear-gradient(90deg, #d4af37, #f2d06b); padding: 20px; border-radius: 10px; text-align: center; color: black; font-weight: bold; font-size: 24px; margin-bottom: 20px; }
    .transfer-box { background-color: #fff3e0; border-left: 5px solid #ff9800; padding: 15px; border-radius: 5px; font-size: 16px; margin-bottom: 15px; color: #333; }
    .bio-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #fafafa; }
    .historic-box { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- INIT ---
if 'initialized' not in st.session_state:
    pilot_verileri = [("Kayra", 10, 9, 9, 9), ("Ahmet", 10, 8, 9, 9), ("Yağız", 10, 8, 8, 8), 
                      ("Barış", 9, 7, 8, 9), ("Kaan", 8, 7, 8, 8), ("Burak", 6, 6, 7, 7), 
                      ("Ömer", 6, 6, 6, 5), ("Yusuf", 6, 4, 5, 4), ("Asil", 5, 5, 5, 4), ("Elif", 4, 4, 4, 5)]
    
    drivers = [Driver(n, "", s, h, b, i) for n, s, h, b, i in pilot_verileri]
    teams = [Team(n) for n in ["Red", "Blue", "Yellow", "Green", "Purple"]]
    
    random.shuffle(drivers)
    for i, d in enumerate(drivers):
        t = teams[i // 2]
        d.team = t.name
        t.add_driver(d)
        
    power_sorted = sorted(drivers, key=lambda d: d.overall_power, reverse=True)
    power_rank_map = {d.name: i+1 for i, d in enumerate(power_sorted)}
    
    circuits = [Circuit("Spa-Francorchamps", 1.2), Circuit("Interlagos", 1.1), Circuit("Miami", 1.0),
                Circuit("Silverstone", 0.9), Circuit("İstanbul Park", 1.3), Circuit("Monza", 0.8), 
                Circuit("Abu Dhabi", 0.8), Circuit("Monaco", 1.4), Circuit("Suzuka", 1.1), 
                Circuit("Australia", 1.0), Circuit("Azerbaijan", 1.3), Circuit("Bahrain", 0.9), 
                Circuit("Canada", 1.1), Circuit("China", 1.0), Circuit("Singapore", 1.4), 
                Circuit("Spain", 0.9), Circuit("COTA", 1.0), Circuit("Jeddah", 1.2), 
                Circuit("Sochi", 0.8), Circuit("Austria", 0.9)]
    
    random.shuffle(circuits)
    st.session_state.drivers = drivers
    st.session_state.retired_drivers = [] 
    st.session_state.teams = teams
    st.session_state.circuits = circuits
    st.session_state.power_rank_map = power_rank_map
    st.session_state.current_year = 2025
    st.session_state.hall_of_fame = []
    st.session_state.development_history = [] 
    st.session_state.transfer_log = [] 
    st.session_state.rookie_pool = list(INITIAL_ROOKIE_POOL)
    st.session_state.current_race_idx = 0
    st.session_state.race_history = []
    st.session_state.all_winners = [] 
    st.session_state.all_poles = []    
    st.session_state.points_history = {d.name: [0] for d in drivers}
    
    # Pist bazlı kazananları tutmak için
    st.session_state.track_winners = {} 
    
    st.session_state.season_started = False
    st.session_state.initialized = True

# --- YAN MENÜ ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1200px-F1.svg.png", width=100)
    st.title(f"Sezon {st.session_state.current_year}")
    
    # 1. Hall of Fame
    if st.session_state.hall_of_fame:
        st.markdown("### 🏛️ Şöhretler Müzesi")
        for entry in st.session_state.hall_of_fame:
            st.caption(f"🏆 {entry['Yıl']}: **{entry['Şampiyon']}**")
        st.markdown("---")

    # 2. Son Kazananlar ve Lider
    if st.session_state.season_started:
        st.markdown("### 🏆 Son Kazananlar")
        if st.session_state.all_winners:
            for i in range(len(st.session_state.all_winners)-1, max(-1, len(st.session_state.all_winners)-6), -1):
                track, winner = st.session_state.all_winners[i]
                st.caption(f"{i+1}. {track}: **{winner}**")
        else:
            st.caption("Henüz yarış yapılmadı.")
        st.markdown("---")
        leader = sorted(st.session_state.drivers, key=lambda d: d.season_points, reverse=True)[0]
        st.metric("Puan Lideri", leader.name, f"{leader.season_points} P")

# --- MENÜ EKRANI ---
if not st.session_state.season_started:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center;'>🏎️ F1 SİMÜLATÖRÜ {st.session_state.current_year}</h1>", unsafe_allow_html=True)
        st.write("")
        if st.button("🏁 SEZONA BAŞLA", type="primary"):
            st.session_state.season_started = True
            st.rerun()
        st.info("Legendary Edition: Radar Analizi, Pist Tarihi ve Biyografiler!")

else:
    # --- ANA SİMÜLASYON EKRANI ---
    current_idx = st.session_state.current_race_idx
    total_races = len(st.session_state.circuits)
    
    st.title(f"{st.session_state.current_year} Sezonu - Hafta {current_idx}/{total_races}")
    
    # --- SEZON BAŞI RAPORLARI ---
    if current_idx == 0:
        if st.session_state.transfer_log:
            with st.expander("🚨 TRANSFER VE EMEKLİLİK HABERLERİ", expanded=True):
                for news in st.session_state.transfer_log:
                    st.markdown(f"<div class='transfer-box'>{news}</div>", unsafe_allow_html=True)
            st.write("")
        if st.session_state.development_history:
            with st.expander("📈 SEZON ÖNCESİ GELİŞİM RAPORU", expanded=False):
                df_dev = pd.DataFrame(st.session_state.development_history)
                st.dataframe(df_dev, hide_index=True, use_container_width=True)

    st.progress(current_idx / total_races)

    # 1. YARIŞ KONTROLÜ
    if current_idx < total_races:
        circuit = st.session_state.circuits[current_idx]
        prev_winner = st.session_state.track_winners.get(circuit.name, "Yok (İlk Sezon)")
        
        col_ctrl, col_info = st.columns([1, 3])
        with col_ctrl:
            st.markdown(f"### 🚩 {circuit.name}")
            st.caption(f"🔙 Geçen Sezon Galibi: **{prev_winner}**") 
            
            if st.button("🚦 YARIŞI BAŞLAT", type="primary"):
                logs, race_res, qual_res, winner, pole = simulate_race_logic(st.session_state.drivers, circuit)
                if winner: 
                    st.session_state.all_winners.append((circuit.name, winner.name))
                    st.session_state.track_winners[circuit.name] = winner.name 
                st.session_state.all_poles.append((circuit.name, pole.name))
                for d in st.session_state.drivers:
                    if d.name in st.session_state.points_history:
                        st.session_state.points_history[d.name].append(d.season_points)
                winner_name = winner.name if winner else None
                st.session_state.race_history.append({"circuit": circuit, "logs": logs, "race_data": race_res, "qual_data": qual_res, "winner_name": winner_name})
                for t in st.session_state.teams: t.calculate_team_points()
                st.session_state.current_race_idx += 1
                st.rerun()

    else:
        # --- SEZON BİTİŞ ---
        st.balloons()
        champion = sorted(st.session_state.drivers, key=lambda d: d.season_points, reverse=True)[0]
        st.markdown(f"<div class='champion-banner'>👑 {st.session_state.current_year} DÜNYA ŞAMPİYONU<br>{champion.name} ({champion.team})<br>{champion.season_points} Puan 👑</div>", unsafe_allow_html=True)
        
        # --- ÖDÜL KÖŞESİ ---
        drivers_all = st.session_state.drivers
        max_wins = max(d.wins for d in drivers_all)
        win_leaders = [d.name for d in drivers_all if d.wins == max_wins]
        max_podiums = max(d.podiums for d in drivers_all)
        podium_leaders = [d.name for d in drivers_all if d.podiums == max_podiums]
        max_poles = max(d.poles for d in drivers_all)
        pole_leaders = [d.name for d in drivers_all if d.poles == max_poles]
        min_dnfs = min(d.dnfs for d in drivers_all)
        safe_drivers = [d.name for d in drivers_all if d.dnfs == min_dnfs]
        best_gain = -99
        rising_stars = []
        for d in drivers_all:
            current_rank = sorted(drivers_all, key=lambda x: x.season_points, reverse=True).index(d) + 1
            gain = st.session_state.power_rank_map.get(d.name, 5) - current_rank
            if gain > best_gain:
                best_gain = gain
                rising_stars = [d.name]
            elif gain == best_gain: rising_stars.append(d.name)
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            st.info(f"🏆 **EN ÇOK GALİBİYET:** {', '.join(win_leaders)} ({max_wins})")
            st.info(f"⭐ **EN ÇOK PODYUM:** {', '.join(podium_leaders)} ({max_podiums})")
            st.success(f"🛡️ **EN AZ KAZA (Safe Driver):** {', '.join(safe_drivers)} ({min_dnfs} DNF)")
        with col_a2:
            st.warning(f"🚦 **POLE KRALI:** {', '.join(pole_leaders)} ({max_poles})")
            st.warning(f"🚀 **YILIN YÜKSELENİ:** {', '.join(rising_stars)} (+{best_gain})")
        
        st.markdown("---")
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.info("Sezon kapandı. Yönetim kurulu ve ödül töreni...")
            if st.button(f"➡️ {st.session_state.current_year + 1} SEZONUNA GEÇ ➡️", type="primary"):
                start_new_season_logic()
                st.rerun()

    # 2. SEKMELİ GÖRÜNÜM
    if st.session_state.race_history:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📝 Yarış Özeti", "📊 Puan Durumu", "📈 Sezon Grafiği", "📚 Biyografiler", "🏰 Tarihi Pistler", "🆚 Kafa Kafaya", "🏅 Tüm Zamanlar"])
        last_race = st.session_state.race_history[-1]
        circ_obj = last_race['circuit']
        
        with tab1:
            if current_idx == 10 and len(st.session_state.race_history) == 10:
                st.info("🎙️ **SEZON ORTASI RÖPORTAJLARI**")
                comments = generate_driver_comments(st.session_state.drivers, st.session_state.power_rank_map)
                c1, c2 = st.columns(2)
                for i, (name, msg, tone) in enumerate(comments):
                    tgt = c1 if i < 5 else c2
                    if tone == "positive": tgt.success(f"**{name}:** {msg}")
                    elif tone == "negative": tgt.error(f"**{name}:** {msg}")
                    else: tgt.info(f"**{name}:** {msg}")
            
            col_img, col_res = st.columns([1, 2])
            with col_img:
                winner_name = last_race.get('winner_name')
                if winner_name:
                    winner_img_path = f"{winner_name}.png"
                    if os.path.exists(winner_img_path):
                        st.markdown(f"<div class='winner-box'><h3>🏆 YARIŞ GALİBİ</h3></div>", unsafe_allow_html=True)
                        st.image(winner_img_path, caption=f"Kazanan: {winner_name}", use_container_width=True)
                    else: st.info(f"🏆 Kazanan: **{winner_name}**")
                st.markdown("---")
                img_path = f"{circ_obj.name}.png"
                if os.path.exists(img_path): st.image(img_path, caption=circ_obj.name, use_container_width=True)
                else: st.caption(f"Pist Görseli Yok: {circ_obj.name}")
                with st.expander("Loglar"):
                    for l in last_race['logs']: st.write(l)
            with col_res:
                st.subheader(f"📊 {circ_obj.name} Sonuç Tablosu")
                st.dataframe(pd.DataFrame(last_race['race_data']), hide_index=True, use_container_width=True)

        with tab2:
            col_p, col_t = st.columns(2)
            drivers_sorted = sorted(st.session_state.drivers, key=lambda d: d.season_points, reverse=True)
            teams_sorted = sorted(st.session_state.teams, key=lambda t: t.season_points, reverse=True)
            with col_p:
                st.markdown("#### Pilotlar Şampiyonası")
                p_data = [{"Sıra": i+1, "Pilot": d.name, "Takım": d.team, "Puan": d.season_points, "W": d.wins, "Pod": d.podiums, "Pole": d.poles} for i, d in enumerate(drivers_sorted)]
                st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)
            with col_t:
                st.markdown("#### Takımlar Şampiyonası")
                t_data = [{"Sıra": i+1, "Takım": f"{t.name} ({', '.join([d.name for d in t.drivers])})", "Puan": t.season_points} for i, t in enumerate(teams_sorted)]
                st.dataframe(pd.DataFrame(t_data), hide_index=True, use_container_width=True)

        with tab3:
            st.markdown("#### 📈 Şampiyonluk Yarışı")
            st.line_chart(pd.DataFrame(st.session_state.points_history))

        with tab4:
            st.subheader("📚 Pilot Biyografileri ve Kariyer İstatistikleri")
            st.caption("Aktif ve emekli tüm pilotların detaylı kariyer verileri.")
            all_bio_drivers = st.session_state.drivers + st.session_state.retired_drivers
            all_bio_drivers.sort(key=lambda x: x.name)
            for driver in all_bio_drivers:
                status_icon = "🟢 Aktif" if driver in st.session_state.drivers else "🔴 Emekli/Ayrıldı"
                with st.expander(f"👤 {driver.name} ({status_icon})"):
                    bc1, bc2 = st.columns([1, 3])
                    with bc1:
                        bio_img = f"{driver.name}.png"
                        if os.path.exists(bio_img): st.image(bio_img, width=150)
                        else: st.info("Resim Yok")
                    with bc2:
                        finish_rate = 0
                        if driver.career_races > 0: finish_rate = ((driver.career_races - driver.career_dnfs) / driver.career_races) * 100
                        st.markdown(f"**Takım:** {driver.team} | **Sezon Sayısı:** {driver.seasons_raced}")
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        col_stat1.metric("Yarış", driver.career_races)
                        col_stat1.metric("Galibiyet", driver.career_wins)
                        col_stat2.metric("Podyum", driver.career_podiums)
                        col_stat2.metric("Pole", driver.career_poles)
                        col_stat3.metric("DNF", driver.career_dnfs)
                        col_stat3.metric("Bitirme %", f"%{finish_rate:.1f}")
                        col_stat4.metric("Şampiyonluk", driver.career_titles)
                        st.markdown("#### 🎖️ Ödüller ve Başarılar")
                        if driver.achievements:
                            for ach in driver.achievements: st.write(f"- {ach}")
                        else: st.write("- Henüz ödül yok.")

        with tab5:
            st.subheader("🏰 Tarihi Pist Kralları")
            all_history_drivers = st.session_state.drivers + st.session_state.retired_drivers
            cols = st.columns(len(HISTORIC_TRACK_TITLES))
            for i, (track, title) in enumerate(HISTORIC_TRACK_TITLES.items()):
                with cols[i]:
                    st.markdown(f"#### {track}")
                    st.markdown(f"**_{title}_**")
                    max_wins = 0
                    leaders = []
                    for d in all_history_drivers:
                        wins = d.specific_race_wins.get(track, 0)
                        if wins > max_wins:
                            max_wins = wins
                            leaders = [d.name]
                        elif wins == max_wins and wins > 0:
                            leaders.append(d.name)
                    st.markdown(f"<div class='historic-box'>", unsafe_allow_html=True)
                    if leaders:
                        st.write(f"👑 {', '.join(leaders)}")
                        st.write(f"**{max_wins} Galibiyet**")
                    else: st.write("Henüz Kral Yok")
                    st.markdown("</div>", unsafe_allow_html=True)

        with tab6:
            st.subheader("🆚 Pilot Karşılaştırma (Radar Analizi)")
            c_sel1, c_sel2 = st.columns(2)
            active_names = [d.name for d in st.session_state.drivers]
            with c_sel1: p1_name = st.selectbox("1. Pilot Seç", active_names, index=0)
            with c_sel2: p2_name = st.selectbox("2. Pilot Seç", active_names, index=1)
            
            p1 = next(d for d in st.session_state.drivers if d.name == p1_name)
            p2 = next(d for d in st.session_state.drivers if d.name == p2_name)
            
            categories = ['Hız', 'Kontrol', 'Fren', 'Zeka']
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=[p1.speed, p1.handling, p1.braking, p1.intelligence], theta=categories, fill='toself', name=p1.name))
            fig.add_trace(go.Scatterpolar(r=[p2.speed, p2.handling, p2.braking, p2.intelligence], theta=categories, fill='toself', name=p2.name))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 11])), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            c_info1, c_info2 = st.columns(2)
            c_info1.info(f"**{p1.name}** Toplam Güç: {p1.overall_power:.1f}")
            c_info2.info(f"**{p2.name}** Toplam Güç: {p2.overall_power:.1f}")

        with tab7: # YENİ: TÜM ZAMANLAR
            st.subheader("🏅 Tüm Zamanların En İyileri")
            st.caption("Aktif ve emekli tüm pilotlar dahil sıralamalar.")
            
            all_drivers_ever = st.session_state.drivers + st.session_state.retired_drivers
            
            def get_top_10(data, key, reverse=True, filter_func=None):
                if filter_func:
                    data = [d for d in data if filter_func(d)]
                sorted_list = sorted(data, key=lambda x: getattr(x, key), reverse=reverse)
                top_10 = sorted_list[:10]
                return [{"Sıra": i+1, "Pilot": d.name, "Takım": d.team, "Değer": getattr(d, key)} for i, d in enumerate(top_10)]

            col_all1, col_all2 = st.columns(2)
            
            with col_all1:
                st.markdown("#### 🏆 En Çok Şampiyonluk")
                df_titles = pd.DataFrame(get_top_10(all_drivers_ever, "career_titles"))
                st.dataframe(df_titles, hide_index=True, use_container_width=True)
                
                st.markdown("#### 🏁 En Çok Galibiyet")
                df_wins = pd.DataFrame(get_top_10(all_drivers_ever, "career_wins"))
                st.dataframe(df_wins, hide_index=True, use_container_width=True)
                
                st.markdown("#### ⚡ En Çok Pole")
                df_poles = pd.DataFrame(get_top_10(all_drivers_ever, "career_poles"))
                st.dataframe(df_poles, hide_index=True, use_container_width=True)

            with col_all2:
                st.markdown("#### 🍾 En Çok Podyum")
                df_podiums = pd.DataFrame(get_top_10(all_drivers_ever, "career_podiums"))
                st.dataframe(df_podiums, hide_index=True, use_container_width=True)
                
                st.markdown("#### 🛡️ En Az DNF (Min. 20 Yarış)")
                # DNF sıralaması (Azdan çoğa) - Sadece tecrübeli pilotlar
                df_safe = pd.DataFrame(get_top_10(all_drivers_ever, "career_dnfs", reverse=False, filter_func=lambda d: d.career_races >= 20))
                if not df_safe.empty:
                    st.dataframe(df_safe, hide_index=True, use_container_width=True)
                else:
                    st.info("Henüz yeterli yarış verisi yok.")