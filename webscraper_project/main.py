import time
import json
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fractions import Fraction
import re

# ---------------------------
# ✅ Hardcoded list of URLs
# ---------------------------
urls = [
    "https://www.food.com/recipe/palak-paneer-indian-fresh-spinach-with-paneer-cheese-25348",
    "https://www.food.com/recipe/oven-baked-vegetarian-samosas-397782"


]

# ---------------------------
# Utility Functions
# ---------------------------

def decimal_to_fraction(value):
    try:
        f = Fraction(value).limit_denominator()
        if f.denominator == 1:
            return str(f.numerator)
        return f"{f.numerator}/{f.denominator}"
    except:
        return str(value)

def extract_quantity(text):
    match = re.match(r"([0-9/.\s]+)", text)
    if match:
        qty_str = match.group(1).strip()
        try:
            qty = sum(Fraction(s) for s in qty_str.split())
            return float(qty)
        except:
            return None
    return None

def remove_quantity(text):
    return re.sub(r"^[0-9/.\s]+", "", text).strip()

def parse_iso8601_duration(duration):
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?'
    match = re.match(pattern, duration)
    if not match:
        return duration
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    if hours and minutes:
        return f"{hours} hours {minutes} minutes"
    elif hours:
        return f"{hours} hours"
    elif minutes:
        return f"{minutes} minutes"
    else:
        return "Not specified"

# ---------------------------
# Scraper Function
# ---------------------------

def scrape_foodcom_recipe(recipe_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(recipe_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        script_tag = soup.find("script", {"type": "application/ld+json"})
        if not script_tag:
            print(f"❌ JSON data not found for {recipe_url}")
            return None

        json_data = json.loads(script_tag.string)

        dish_name = json_data.get("name", "Unknown Dish")
        ready_in_time = parse_iso8601_duration(json_data.get("totalTime", "Not Available"))

        recipe_yield = json_data.get("recipeYield", "1")
        try:
            yield_number = int(re.search(r'\d+', str(recipe_yield)).group())
        except:
            yield_number = 1

        ingredients = []
        for item in json_data.get("recipeIngredient", []):
            qty = extract_quantity(item)
            ing = remove_quantity(item)

            if qty is not None and qty > 0 and yield_number != 0:
                scaled_qty = qty / yield_number
                qty_str = decimal_to_fraction(scaled_qty)
                ingredients.append(f"{qty_str} {ing}".strip())
            else:
                ingredients.append(ing.strip())

        if not ingredients:
            ingredients = ["Ingredients not found"]

        directions = [step.get("text", "") for step in json_data.get("recipeInstructions", [])]
        if not directions:
            directions = ["Directions not found"]

        recipe_data = {
            "Dish Name": dish_name,
            "Ready In Time": ready_in_time,
            "Ingredients": "\n".join(ingredients),
            "Directions": "\n".join(directions)
        }

        return recipe_data

    except Exception as e:
        print(f"Error scraping {recipe_url}: {e}")
        return None
    finally:
        driver.quit()

# ---------------------------
# Save to CSV
# ---------------------------

def save_to_csv(data, filename="rec.csv"):
    df = pd.DataFrame([data])
    df.to_csv(filename, mode="a", index=False, header=not pd.io.common.file_exists(filename))
    print(f"✅ Data saved to {filename}")

# ---------------------------
# 🚀 Auto Scrape (No User Input)
# ---------------------------

for url in urls:
    print(f"\n🌐 Scraping: {url}")
    recipe_data = scrape_foodcom_recipe(url)
    if recipe_data:
        print("\n📌 Extracted Recipe Data:")
        print(f"🍽️ Dish Name: {recipe_data['Dish Name']}")
        print(f"⏱️ Ready In Time: {recipe_data['Ready In Time']}")
        print(f"\n📝 Ingredients for 1 serving:\n{recipe_data['Ingredients']}")
        print(f"\n👨‍🍳 Directions:\n{recipe_data['Directions']}")
        save_to_csv(recipe_data)

print("\n🎉 All recipes scraped successfully!")
