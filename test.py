import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import time

# ရခိုင်ပြည်နယ်သတင်းအရင်းအမြစ်များ
SOURCES = {
    "RFA Burmese - Rakhine": "https://www.rfa.org/burmese/news/rakhine",
    "VOA Burmese - Rakhine": "https://burmese.voanews.com/z/4847",
    "The Rakhine Times": "https://www.rakhinetimes.com",
    "Rakhine News Agency": "https://rakhine.news",
    "BBC News - Myanmar": "https://www.bbc.com/news/world-asia-asia-pacific-16967372",
    "Narinjara News": "https://www.narinjara.com",
    "DMG (Development Media Group)": "https://www.dmg.com.bd",
    "Myanmar Now": "https://myanmar-now.org/mm",
    "DVB Burmese": "https://burmese.dvb.no",
    "ဧရာဝတီ (The Irrawaddy)": "https://burma.irrawaddy.com"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "my-MM,my;q=0.9,en-US;q=0.8,en;q=0.7"
}

# ရခိုင်နဲ့ဆိုင်တဲ့ သော့ချက်စာလုံးများ
RAKHINE_KEYWORDS = [
    "ရခိုင်", "ရခိုင်ပြည်", "အာရကန်", "Arakan", "Rakhine",
    "စစ်တွေ", "Sittwe", "မြောက်ဦး", "Mrauk U",
    "မောင်တော", "Maungdaw", "ဘူးသီးတောင်", "Buthidaung",
    "ရသေ့တောင်", "Rathedaung", "ပုဏ္ဏားကျွန်း", "Ponnagyun",
    "ကျောက်တော်", "Kyauktaw", "မင်းပြား", "Minbya",
    "မြေပုံ", "Mrauk U", "တောင်ကုတ်", "Taungup",
    "သံတွဲ", "Thandwe", "ဂွ", "Gwa",
    "ကျောက်ဖြူ", "Kyaukphyu", "ရမ်းဗြဲ", "Ramree",
    "မန်း", "Man Aung", "စစ်တကောင်း", "Chittagong",
    "ရိုဟင်ဂျာ", "Rohingya",
    "အာရက္ခတပ်တော်", "AA", "Arakan Army",
    "ရခိုင်ပြည်နယ်", "Rakhine State"
]

def is_rakhine_related(text):
    """စာသားတစ်ခုက ရခိုင်နဲ့ဆိုင်လားဆိုတာ စစ်ဆေးခြင်း"""
    text_lower = text.lower()
    for keyword in RAKHINE_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

def fetch_generic(url, name, parser="html.parser"):
    """အထွေထွေ webpage တစ်ခုမှ သတင်းခေါင်းစဉ်များ ရယူခြင်း"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, parser)
        headlines = []
        
        # h1, h2, h3, h4 tags များကို ရှာဖွေခြင်း
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            a_tag = tag.find("a") or tag
            text = a_tag.get_text(strip=True)
            link = a_tag.get("href", "") if a_tag.name == "a" else ""
            
            # Relative link ကို absolute link အဖြစ်ပြောင်းခြင်း
            if link and not link.startswith("http"):
                from urllib.parse import urljoin
                link = urljoin(url, link)
            
            if text and len(text) > 10:
                headlines.append({
                    "title": text,
                    "url": link,
                    "source": name
                })
        
        # ရခိုင်သတင်းတွေကို ဦးစားပေးပြီး ပြသမယ်
        rakhine_news = [h for h in headlines if is_rakhine_related(h["title"])]
        other_news = [h for h in headlines if not is_rakhine_related(h["title"])]
        
        # ရခိုင်သတင်း ၁၀ ခုနဲ့ အခြားသတင်း ၅ ခု
        result = rakhine_news[:10] + other_news[:5]
        return result if result else [{"title": f"No headlines found from {name}", "url": "", "source": name}]
    
    except requests.exceptions.ConnectionError:
        return [{"title": f"⚠️ No internet connection - {name}", "url": "", "source": name}]
    except requests.exceptions.Timeout:
        return [{"title": f"⏱️ Timeout - {name}", "url": "", "source": name}]
    except Exception as e:
        return [{"title": f"Error fetching {name}: {str(e)[:50]}", "url": "", "source": name}]

def fetch_narinjara():
    """Narinjara News မှ ရခိုင်သတင်းများ"""
    try:
        r = requests.get("https://www.narinjara.com", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        headlines = []
        
        for h2 in soup.find_all("h2"):
            a_tag = h2.find("a")
            if a_tag:
                text = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if text and len(text) > 10:
                    headlines.append({
                        "title": text,
                        "url": link if link.startswith("http") else f"https://www.narinjara.com{link}",
                        "source": "Narinjara News"
                    })
        return headlines[:10] if headlines else [{"title": "No headlines from Narinjara", "url": "", "source": "Narinjara News"}]
    except Exception as e:
        return [{"title": f"Error fetching Narinjara: {str(e)[:50]}", "url": "", "source": "Narinjara News"}]

def fetch_irrawaddy():
    """ဧရာဝတီ (The Irrawaddy) မှ ရခိုင်သတင်းများ"""
    try:
        r = requests.get("https://burma.irrawaddy.com/category/rakhine", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        headlines = []
        
        for article in soup.find_all("article"):
            h2 = article.find("h2")
            if h2:
                a_tag = h2.find("a")
                if a_tag:
                    text = a_tag.get_text(strip=True)
                    link = a_tag.get("href", "")
                    if text:
                        headlines.append({
                            "title": text,
                            "url": link,
                            "source": "ဧရာဝတီ (The Irrawaddy)"
                        })
        return headlines[:10] if headlines else [{"title": "No headlines from Irrawaddy", "url": "", "source": "ဧရာဝတီ"}]
    except Exception as e:
        return [{"title": f"Error fetching Irrawaddy: {str(e)[:50]}", "url": "", "source": "ဧရာဝတီ"}]

def fetch_dvb():
    """DVB Burmese မှ ရခိုင်သတင်းများ"""
    try:
        r = requests.get("https://burmese.dvb.no/category/rakhine-state", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        headlines = []
        
        for h2 in soup.find_all("h2"):
            a_tag = h2.find("a")
            if a_tag:
                text = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if text and len(text) > 10:
                    headlines.append({
                        "title": text,
                        "url": link,
                        "source": "DVB Burmese"
                    })
        return headlines[:10] if headlines else [{"title": "No headlines from DVB", "url": "", "source": "DVB Burmese"}]
    except Exception as e:
        return [{"title": f"Error fetching DVB: {str(e)[:50]}", "url": "", "source": "DVB Burmese"}]

def fetch_myanmar_now():
    """Myanmar Now မှ ရခိုင်သတင်းများ"""
    try:
        r = requests.get("https://myanmar-now.org/mm/search?q=ရခိုင်", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        headlines = []
        
        for h3 in soup.find_all("h3"):
            a_tag = h3.find("a")
            if a_tag:
                text = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if text and len(text) > 10:
                    headlines.append({
                        "title": text,
                        "url": link,
                        "source": "Myanmar Now"
                    })
        return headlines[:10] if headlines else [{"title": "No headlines from Myanmar Now", "url": "", "source": "Myanmar Now"}]
    except Exception as e:
        return [{"title": f"Error fetching Myanmar Now: {str(e)[:50]}", "url": "", "source": "Myanmar Now"}]

def fetch_rakhine_times():
    """The Rakhine Times မှ သတင်းများ"""
    return fetch_generic("https://www.rakhinetimes.com", "The Rakhine Times")

def fetch_all_sources():
    """သတင်းရင်းမြစ်အားလုံးမှ တစ်ပြိုင်နက်ရယူခြင်း"""
    all_news = {}
    
    print("\n🔍 Fetching Rakhine-related news...")
    
    # Narinjara News (ရခိုင်သတင်းအေဂျင်စီ)
    print("  📡 Narinjara News...")
    all_news["Narinjara News"] = fetch_narinjara()
    time.sleep(1)
    
    # ဧရာဝတီ
    print("  📡 ဧရာဝတီ (The Irrawaddy)...")
    all_news["ဧရာဝတီ (The Irrawaddy)"] = fetch_irrawaddy()
    time.sleep(1)
    
    # DVB Burmese
    print("  📡 DVB Burmese...")
    all_news["DVB Burmese"] = fetch_dvb()
    time.sleep(1)
    
    # Myanmar Now
    print("  📡 Myanmar Now...")
    all_news["Myanmar Now"] = fetch_myanmar_now()
    time.sleep(1)
    
    # VOA Burmese - Rakhine
    print("  📡 VOA Burmese...")
    all_news["VOA Burmese"] = fetch_generic(SOURCES["VOA Burmese - Rakhine"], "VOA Burmese")
    time.sleep(1)
    
    # RFA Burmese - Rakhine
    print("  📡 RFA Burmese...")
    all_news["RFA Burmese"] = fetch_generic(SOURCES["RFA Burmese - Rakhine"], "RFA Burmese")
    time.sleep(1)
    
    # BBC Myanmar
    print("  📡 BBC News...")
    all_news["BBC News"] = fetch_generic(SOURCES["BBC News - Myanmar"], "BBC News")
    time.sleep(1)
    
    # The Rakhine Times
    print("  📡 The Rakhine Times...")
    all_news["The Rakhine Times"] = fetch_rakhine_times()
    time.sleep(1)
    
    return all_news

def display_news(all_news):
    """သတင်းများကို လှပစွာပြသခြင်း"""
    print("\n" + "=" * 60)
    print("📰 ရခိုင်ပြည်နယ်သတင်းများ - RAKHINE STATE NEWS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    news_count = 0
    rakhine_count = 0
    
    for source, headlines in all_news.items():
        if not headlines:
            continue
            
        print(f"\n{'─' * 50}")
        print(f"📰 {source}")
        print(f"{'─' * 50}")
        
        for i, h in enumerate(headlines, 1):
            title = h["title"]
            url = h.get("url", "")
            
            # ရခိုင်သတင်းဆိုရင် အထူးအမှတ်အသား
            if is_rakhine_related(title):
                print(f"  🔴 {i}. {title}")
                rakhine_count += 1
            else:
                print(f"     {i}. {title}")
            
            if url:
                print(f"       └─ {url}")
            
            news_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"📊 စုစုပေါင်းသတင်း: {news_count} ခု")
    print(f"🔴 ရခိုင်နဲ့ဆိုင်သော: {rakhine_count} ခု")
    print(f"{'=' * 60}")

def save_to_json(data, filename=None):
    """JSON ဖိုင်အဖြစ် သိမ်းဆည်းခြင်း"""
    if filename is None:
        filename = f"rakhine_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved to {filename}")
    return filename

def save_to_txt(data, filename=None):
    """စာသားဖိုင်အဖြစ် သိမ်းဆည်းခြင်း - Offline ဖတ်ရန်အဆင်ပြေ"""
    if filename is None:
        filename = f"rakhine_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("📰 ရခိုင်ပြည်နယ်သတင်းများ - RAKHINE STATE NEWS\n")
        f.write(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")
        
        for source, headlines in data.items():
            if not headlines:
                continue
            f.write(f"\n{'─' * 50}\n")
            f.write(f"📰 {source}\n")
            f.write(f"{'─' * 50}\n")
            
            for i, h in enumerate(headlines, 1):
                title = h["title"]
                url = h.get("url", "")
                
                if is_rakhine_related(title):
                    f.write(f"  🔴 {i}. {title}\n")
                else:
                    f.write(f"     {i}. {title}\n")
                
                if url:
                    f.write(f"       └─ {url}\n")
    
    print(f"\n✅ Saved to {filename}")
    
    # ဖိုင်အရွယ်အစားပြသခြင်း
    size = os.path.getsize(filename)
    print(f"   📦 File size: {size:,} bytes")
    
    return filename

def offline_viewer():
    """သိမ်းထားတဲ့ဖိုင်တွေကို Offline ဖတ်ခြင်း"""
    import glob
    
    txt_files = glob.glob("rakhine_news_*.txt")
    json_files = glob.glob("rakhine_news_*.json")
    
    saved_files = txt_files + json_files
    
    if not saved_files:
        print("\n📭 No saved news files found!")
        return
    
    print("\n📂 Saved news files:")
    for i, f in enumerate(saved_files, 1):
        size = os.path.getsize(f)
        modified = datetime.fromtimestamp(os.path.getmtime(f))
        print(f"  {i}. {f} ({size:,} bytes - {modified.strftime('%Y-%m-%d %H:%M')})")
    
    choice = input("\nSelect file number to view (or Enter to skip): ").strip()
    
    if choice and choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(saved_files):
            filename = saved_files[idx]
            print(f"\n{'=' * 60}")
            print(f"📖 Viewing: {filename}")
            print(f"{'=' * 60}")
            
            with open(filename, "r", encoding="utf-8") as f:
                print(f.read())

def auto_fetch_loop():
    """အလိုအလျောက် သတင်းစုဆောင်းခြင်း (Auto-refresh)"""
    print("\n⏰ Auto-fetch mode:")
    print("  သတင်းများကို မိနစ်ပိုင်းခြားပြီး အလိုအလျောက် ထပ်မံရယူမည်")
    
    try:
        interval = int(input("  Interval in minutes (default 30): ").strip() or "30")
    except ValueError:
        interval = 30
    
    print(f"\n🔄 Auto-fetching every {interval} minute(s)...")
    print("   Press Ctrl+C to stop\n")
    
    cycle = 0
    while True:
        cycle += 1
        print(f"\n{'#' * 60}")
        print(f"  Cycle #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#' * 60}")
        
        all_news = fetch_all_sources()
        display_news(all_news)
        
        # Auto-save
        filename = save_to_txt(all_news)
        save_to_json(all_news)
        
        print(f"\n⏳ Next fetch in {interval} minute(s)...")
        time.sleep(interval * 60)

def main():
    while True:
        print("\n" + "=" * 60)
        print("📰 ရခိုင်ပြည်နယ်သတင်းစုဆောင်းကိရိယာ")
        print("   RAKHINE STATE NEWS COLLECTOR v2.0")
        print("=" * 60)
        print("   🌐 အွန်လိုင်းသတင်းများ")
        print("   📴 Offline ဖတ်ရှုနိုင်")
        print("   🔴 ရခိုင်သတင်းများကို ဦးစားပေးဖော်ပြ")
        print("=" * 60)
        
        print("\n📋 Main Menu:")
        print("  1. 🔄 Fetch latest Rakhine news")
        print("  2. 📂 View saved news (offline)")
        print("  3. ⏰ Auto-fetch mode")
        print("  4. ❌ Exit")
        
        choice = input("\n  Choose (1-4): ").strip()
        
        if choice == "1":
            all_news = fetch_all_sources()
            display_news(all_news)
            
            print("\n💾 Save options:")
            print("  1. Save as TXT (recommended for offline)")
            print("  2. Save as JSON")
            print("  3. Save both")
            print("  4. Skip")
            
            save_choice = input("\n  Choose (1-4): ").strip()
            
            if save_choice == "1":
                save_to_txt(all_news)
            elif save_choice == "2":
                save_to_json(all_news)
            elif save_choice == "3":
                save_to_txt(all_news)
                save_to_json(all_news)
            
            input("\n  Press Enter to continue...")
            
        elif choice == "2":
            offline_viewer()
            input("\n  Press Enter to continue...")
            
        elif choice == "3":
            try:
                auto_fetch_loop()
            except KeyboardInterrupt:
                print("\n\n⏹️ Auto-fetch stopped.")
                input("  Press Enter to continue...")
            
        elif choice == "4":
            print("\n👋 ကျေးဇူးတင်ပါတယ်! Thank you for using Rakhine News Collector!")
            break
        
        else:
            print("\n⚠️ Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")