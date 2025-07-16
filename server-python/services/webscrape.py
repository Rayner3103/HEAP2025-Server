#imports
import json
import requests
from bs4 import BeautifulSoup
from lxml import etree
import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

from services import event as event_service
from services import database as database_service

# Code is structured as the following:
#   (1) Helper functions
#   (2) Scraping for websites
#   (3) Funciton to run all the code
#   (4) Sample run code

# (1) ---------------------- HELPER FUNCTIONS ----------------------

def debug_mode_input(msg=""):
    # Function called when DEBUG_MODE is True and there is a critical error
    print(msg)
    user_input = input("To exit, enter 'n'. Else, press any key to continue: ")
    if user_input.lower() == "n":
        exit()

def deCFEmail(fp):
    # This function decodes the emails which are blocked when scraping websites
    # Used by parse_paragraphs()
    # Input: data-cfemail attribute of html tag containing email
    # Output: email string
    try:
        r = int(fp[:2],16)
        email = ''.join([chr(int(fp[i:i+2], 16) ^ r) for i in range(2, len(fp), 2)])
        return email
    except (ValueError):
        pass

def parse_paragraphs(paragraphs):
    # Helper function to extract out all the text in a nested html paragraph properly.
    # Input: etree element with the paragraphs to be extracted out
    # Output: str with proper formating for display
    # This function formats the following:
    #   (1) Protected emails
    #   (2) Newlines where necessary
    #   (3) Lists items
    #   (4) html/xml special characters
    return_str = ""
    for para in paragraphs:
        write = True
        # Ignore if it is a blank paragraph
        if str(etree.tostring(para, method="text", encoding='unicode')) == "": continue # type: ignore
        # Extract out in html to handle tags
        html = str(etree.tostring(para, method="html", encoding='unicode')) # type: ignore
        # Decrypt emails
        if "data-cfemail=" in html:
            return_str += str(deCFEmail(para.xpath('.//a/@data-cfemail')[0])) + "\n"
            continue
        # Change the following tags which usually automatically creates a newline to \n
        newline_tags = (
            '<br>', '</li>', '<p>', '</p>',
            '<h1>', '</h1>', '<h2>', '</h2>',
            '<h3>', '</h3>', '<h4>', '</h4>',
            '<h5>', '</h5>', '<h6>', '</h6>',
            )
        for tag in newline_tags:
            html = html.replace(tag, "\n")
        html = html.replace("<li>", "\n-")
        # Only add in text that are outside the html tags <>
        # i.e. remove the other tags like <strong> or <a>
        for ch in html:
            if write and ch == "<":
                write = False
            if not write and ch == ">":
                write = True
                continue
            if write:
                return_str += ch
        return_str += "\n"
    # Cleaning up the text
    while "\n\n" in return_str:
        return_str = return_str.replace("\n\n", "\n")
    return_str = return_str.replace("-\n", "- ")
    # Handle special html/xml characters
    soup = BeautifulSoup(f"<p>{return_str.strip()}<p>", 'html.parser')
    return_str = soup.get_text().strip("\n")
    return return_str

def get_gemini_model(new=False):
    if 'current_model' not in globals() or 'MODELS' not in globals():
        if PRINT_MODE == 3 : print("get_gemini_model(): First Gemini call, creating global variables.")
        global MODELS 
        global current_model
        MODELS = (
            'gemini-2.0-flash', # Ideal
            'gemini-2.5-flash', # Slow output due to thinking
            'gemini-2.5-flash-lite-preview-06-17', # Low request limit
            'gemini-2.0-flash-lite', # Still works I guess
        )
        current_model = 0
        if PRINT_MODE == 3 : print("get_gemini_model(): Successful.")
    if new:
        if PRINT_MODE == 3 : print("get_gemini_model(): Switching models.")
        if current_model + 1 == len(MODELS):
            # If all models have been cycled through
            if PRINT_MODE >= 2 : print("get_gemini_model(): ERROR: All models have exceeded their rate limits. Please try again later or add more models.")
            if DEBUG_MODE: debug_mode_input()
        if PRINT_MODE == 3 : print(f"get_gemini_model(): Switching from {MODELS[current_model]}", end=" ")
        current_model = (current_model + 1)
        if PRINT_MODE == 3 : print(f"to {MODELS[current_model]}")
    return MODELS[current_model]

def gemini_request(prompt, content):
    # Makes a call to the gemini API while handling rate limit restrictions
    # Input: prompt & content
    # Output: string response from gemini
    if PRINT_MODE == 3 : print(f"gemini_request(): Creating gemini request\n\tPrompt: {prompt}\n\tContent:{content}")
    sleep_time = 25
    load_dotenv()
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    while True:
        try:
            response = client.models.generate_content(
                # model='gemini-2.5-flash',
                model=get_gemini_model(),
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=[prompt]
                ),       
            )
            break

        except genai.errors.ClientError: # type: ignore
            # There can be 2 scenarios where a ClientError is raised:
            #   (1) The request limit per minute is hit
            #   (2) The request limit for the model per day is hit
            if sleep_time < 100:
                # Case (1): The request limit per minute is hit
                # Apply a delay before trying again
                if PRINT_MODE >= 2 : print(f"gemini_request(): Rate limit exceeded. Waiting {sleep_time} seconds.")
                time.sleep(sleep_time)
                sleep_time *= 2
            else:
                # Case 2: The request limit for the model per day is hit
                # Change the model used
                if PRINT_MODE >= 2 : print(f"gemini_request(): Error: Rate limit for current model has been reached.")
                get_gemini_model(new=True)
                # Reset the sleep time
                sleep_time=25

        except genai.errors.ServerError: # type: ignore
            # Error on Google's end
            # Continue using the same model and retry after delay
            if PRINT_MODE >= 2 : print(f"gemini_request(): Model is overloaded. Waiting {sleep_time} seconds.")
            time.sleep(sleep_time)
            sleep_time *= 2
        
    if PRINT_MODE == 3 : print(f"gemini_request(): Success.")
    return str(response.text).strip('\n')

def classify(data):
    # Calls gemini to classify the code
    # Removes events which gemini determines is useless
    length = len(data)
    if PRINT_MODE >= 2 : print(f"classify(): Starting classification of {length} events.")
    return_data = []
    for i in range(len(data)):
        if PRINT_MODE >= 2 : print(f"classify(): Classifying {i+1}/{length} event.")
        response = gemini_request(
            prompt="""
                You will now take on the role of a data engineer classifying data. You will be provided information of independent isolated events in a json format. Each json represents an independent event which is unrelated to other events. Based on the information provided for
                an event, you are to determine if the event should be in the database. To be included in the database, the event must be academic related and be of one of the following categories: 'Talks', 'Workshops', 'Case Comps', 'Hackathons'. Should the event not fulfil any criteria,
                you are to reply with: 'ERROR, reasoning'. Otherwise, you are to determine which category it falls in, along with your confidence in your categorization in percentage. You are to only reply with both information in the format: 'category, confidence'.
            """,
            content=json.dumps(data[i])
        )
        if PRINT_MODE == 3 : print(f"classify(): {data[i]['title']}: {response}")
        eventType, confidence = response.split(", ", 1) # Confidence can be logged
        if eventType == "ERROR": continue
        data[i]['eventType'] = eventType
        if PRINT_MODE == 3 : print(f"Added: {data[i]['title']}")
        return_data.append(data[i])
    if PRINT_MODE >= 2 : print(f"classify(): Done.")
    return return_data

def parse_descriptions(brief_desc, desc):
    # Helper function to:
    #   (1) Set the brief and full description based on the length
    #   (2) Check if brief description is less than 30 words
    #   (3) Use AI to generate a brief description should it be necessary
    if PRINT_MODE == 3 : print(f"parse_descriptions(): Starting.")
    if len(brief_desc) > len(desc):
        brief_desc, desc = desc, brief_desc
    
    # Cases where there needs to be a new description generated:
    #   (1) No brief_desc
    #   (2) brief_desc too long
    if len(brief_desc) == 0 or len(brief_desc.split(" ")) > 30:
        if PRINT_MODE == 3 : print(f"parse_descriptions(): Generating new brief description.")
        brief_desc = gemini_request(
            prompt="""
                You will now take on the role of a UX designer. You are provided with the description of
                an event. You are to summarize the description in 30 words or less and provide a brief 
                description of the event such that it would catch a user's attention to find out more
                about the event. Return only the attention grabbing description without any formating, 
                titles, headings, special characters or newlines.
            """,
            content=desc if len(brief_desc) == 0 else brief_desc
        )
        if PRINT_MODE == 3 : print(f"parse_descriptions(): Successful.\n\tResponse: {brief_desc}")
    if PRINT_MODE == 3 : print(f"parse_descriptions(): Done.")
    return brief_desc, desc

def get_mode_from_location(location):
    if PRINT_MODE == 3 : print(f"get_mode_from_location(): Determining mode from location.")
    response = gemini_request(prompt="""
            You will now take on the role of a data engineer. You are provided with the location of
            an event. You are to classify the location into 1 of 4 categories: offline, online,
            hybrid or TBA. Where hybrid implies that the event takes place both physically and online
            while TBA implies that the location is yet to be announced. If you are unsure, reply 
            with unknown. You are only allowed to respond with any of the following 5 words: offline,
            online, hybrid, TBA, unknown.
        """,
        content=location)
    response = response.lower()
    if response not in ('offline', 'online', 'hybrid', 'tba', 'unknown'):
        if PRINT_MODE == 3 : 
            print(f"""
                get_mode_from_location(): Error: gemini_request did not return expected result.
                    Expected: offline, online, hybrid, TBA or unknown
                    Response: {response}
            """)
        response = 'unknown'
    if PRINT_MODE == 3 : print(f"get_mode_from_location(): Successfully classfied as {response}.")
    return response
    
def format_date(date_str):
    # Standardizes date format across different websites
    # Input: date string from scraping
    # Output: date string in the format DD FullMonth YYYY, or input date string if format cannot be identified
    if PRINT_MODE == 3 : print(f"format_date(): Formatting date.")
    if date_str == "":
        if PRINT_MODE == 3 : print(f"format_date(): Empty date.")
        return None
    DATE_STR_FORMATS = (
        "%b %d, %Y", # SG Innovate date format
        "%B %d, %Y", # Cordy date format
    )
    for format in DATE_STR_FORMATS:
        try:
            date = datetime.strptime(date_str, format)
            if PRINT_MODE == 3 : print(f"format_date(): Successfully formatted date.")
            return date.strftime("%d %B %Y")
        except Exception as e:
            continue
    if PRINT_MODE >= 2 : print(f"format_date(): ERROR: Date format not recognized.\nInput: {date_str}.")
    if DEBUG_MODE : debug_mode_input()
    return None

def insert_to_database(data):
    # If it is the first time running, get the root user login details
    if 'user_id' not in globals():
        global user_id
        user_id = database_service.get_root_user_id()

    # Insert entry into the database
    # Detects if it was not inserted properly
    for entry in data:
        try:
            signup_link = entry['signupLink']
            title = entry['title']
            event_id = event_service.check_has_event_by_signup_link_and_name(signup_link, title)
            if event_id:
                # update event if it is already in the db
                event_service.edit_event(event_id, entry)
                continue
            event_service.create_event(entry, user_id=user_id)
        except Exception as e:
            print(f"Encountered error ${e}. Unable to add event ${title} (${signup_link}) into the db")
        # if return_str != signup_link:
        #     if PRINT_MODE >= 2 : print(f"insert_to_database(): Error: Unable to insert data entry with link {signup_link}.")
        #     if DEBUG_MODE : debug_mode_input()

# (2) ---------------------- SCRAPER FUNCTIONS ----------------------

def scrape_cordy():
    # The following fields cannot be found from the cordy website:
    #   (1) startTime
    #   (2) endTime
    #   (3) mode
    #   (4) venue
    if PRINT_MODE >= 2 : print(f"scrape_cordy(): Starting.")
    URL = "https://www.cordy.sg/"
    while True:
        response = requests.get(URL)
        if response.status_code == 200:
            if PRINT_MODE == 3 : print(f"scrape_cordy(): Connection successful.")
            soup = BeautifulSoup(response.content, 'html5lib')
            break
        else:
            if PRINT_MODE >= 2 : print(f"scrape_cordy(): Connection unsuccessful.\nError: {response.status_code} - {response.text}")
            if DEBUG_MODE : debug_mode_input()
            if PRINT_MODE >= 2 : print(f"scrape_cordy(): Retrying in 10 seconds")
            time.sleep(10)

    events = []
    # Find all event blocks
    for event in soup.select('.opp-cms-wrapper.w-dyn-item'):
        # Title
        title = event.select_one('.text-block-6')
        title = title.get_text(strip=True) if title else None

        # Link
        link = event.select_one('.opp-cms-link-item')
        link = "https://www.cordy.sg" + str(link['href']) if link else None

        # Date
        date = event.select_one('.text-block-10')
        date = date.get_text(strip=True) if date else None

        # Tags
        tags = [tag.get_text(strip=True) for tag in event.select('.text-block-18')]

        # Organisation
        org = event.select_one('.opp-cms-organisation')
        org = org.get_text(strip=True) if org else None

        # Brief Description
        desc = event.select_one('.opp-cms-caption')
        desc = desc.get_text(strip=True) if desc else None

        # Image
        img = event.select_one('.opp-cms-thumbnail img')
        img = img['src'] if img else None

        events.append({
            "title": title,
            "link": link,
            "signupDeadline": format_date(date),
            "tags": tags,
            "organisation": org,
            "briefDescription": desc,
            "image": img,
            "origin": "web",
            "mode": "unknown",
        })
        if PRINT_MODE == 3 : print(f"scrape_cordy(): Successfully added {title}")
        

    if PRINT_MODE == 3 : print(f"scrape_cordy(): All basic information added. Now scraping for more information.")
    for i in range(len(events)):
        # Go into each link to find:
        #   (1) Full Description
        #   (2) Signup Link
        event = events[i]
        url = event['link']
        if PRINT_MODE == 3 : print(f"scrape_cordy(): Accessing {url}.")
        while True:
            response = requests.get(url)
            if response.status_code == 200:
                if PRINT_MODE == 3 : print(f"scrape_cordy(): Successful.")
                soup = BeautifulSoup(response.content, 'html.parser')
                dom = etree.HTML(text=str(soup), parser=None)

                # Get the full description
                paragraphs = dom.xpath('/html/body/div[3]/div/div[3]/div[3]')[0]
                description = parse_paragraphs(paragraphs)

                # Swap brief and full description based on length
                events[i]['briefDescription'], events[i]['description'] = parse_descriptions(events[i]['briefDescription'], description)
                
                # Extract sign up link
                signup_link = dom.xpath('/html/body/div[3]/div/a')[0].attrib['href']
                events[i]['signupLink'] = signup_link
                if PRINT_MODE == 3 : print(f"scrape_cordy(): Successfully added event.")
                break
            else:
                if PRINT_MODE >= 2 : print(f"scrape_cordy(): Connection unsuccessful.\nError: {response.status_code} - {response.text}")
                if DEBUG_MODE : debug_mode_input()
                if PRINT_MODE >= 2 : print(f"scrape_cordy(): Retrying in 10 seconds")
                time.sleep(10)
    
    if PRINT_MODE == 3 : print(f"scrape_cordy(): Cordy information added. Now classifying and filtering events.")
    return list(classify(events))

def scrape_innovate():
    # The following fields cannot be found from the cordy website:
    #   (1) organisation
    #   (2) startTime & endTime due to inconsistency -> schedule is put in additional information
    if PRINT_MODE >= 2 : print(f"scrape_innovate(): Starting.")
    URL = "https://www.sginnovate.com/events"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    while True:
        response = requests.get(URL, headers=headers)
        if response.status_code == 200:
            if PRINT_MODE == 3 : print(f"scrape_innovate(): Connection successful.")
            # Parse with etree for XPath
            soup = BeautifulSoup(response.content, 'html.parser')
            dom = etree.HTML(text=str(soup), parser=None)
            break
        else:
            if PRINT_MODE >= 2 : print(f"scrape_innovate(): Connection unsuccessful.\nError: {response.status_code} - {response.text}")
            if DEBUG_MODE : debug_mode_input()
            if PRINT_MODE >= 2 : print(f"scrape_innovate(): Retrying in 10 seconds")
            time.sleep(10)
        
    # Find event cards using XPath
    event_cards = dom.xpath('//div[contains(@class, "col-md-6 col-lg-4 mb-4")]')
    
    events = []
    for card in event_cards:
        # Skip promotional cards
        if card.xpath('.//img[contains(@src, "Host-an-event")]'):
            continue
        # Extract data using XPath
        title = card.xpath('.//h4/a/text()')
        link = card.xpath('.//h4/a/@href')
        image = card.xpath('.//img/@src')
        date = card.xpath('.//p/text()')
        register_link = card.xpath('.//div[contains(@class, "register-hld")]//a/@href')
        tags = card.xpath('.//a[contains(@href, "search-events")]/text()')
        
        # Build event dict
        event = {
            'title': title[0].strip() if title else '',
            'link': 'https://www.sginnovate.com' + link[0] if link else '',
            'image': image[0] if image else '',
            'signupDeadline': format_date(date[0].strip()) if date else None,
            'signupLink': register_link[0] if register_link else '',
            'tags': [tag.strip() for tag in tags if tag.strip() and not tag.startswith('+')],
            'origin': 'web'
        }
        
        # Only add if has title
        if event['title']:
            events.append(event)
            if PRINT_MODE == 3 : print(f"scrape_innovate(): Successfully added {event['title']}")
    
    if PRINT_MODE == 3 : print(f"scrape_innovate(): All basic information added. Now scraping for more information.")
    for i in range(len(events)):
        # Go into each link to find:
        #   (1) Brief and full Description
        #   (2) Schedule
        #   (3) Venue + Mode
        event = events[i]
        url = event['link']
        if PRINT_MODE == 3 : print(f"scrape_innovate(): Accessing {url}.")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        while True:
            if response.status_code == 200:
                if PRINT_MODE == 3 : print(f"scrape_innovate(): Successful.")
                # Parse with etree for XPath
                soup = BeautifulSoup(response.content, 'html.parser')
                dom = etree.HTML(text=str(soup), parser=None)

                # Extract brief description
                paragraphs = dom.xpath('//*[@id="content"]/section[1]/div/div/div/div/div/div[2]/article/div[1]')[0]
                brief_description = parse_paragraphs(paragraphs)

                # Extract description
                paragraphs = dom.xpath('//*[@id="content"]/section[1]/div/div/div/div/div/div[2]/article/div[3]/section[1]')[0]
                description = parse_paragraphs(paragraphs)

                # Assign to the json based on length
                events[i]['briefDescription'], events[i]['description'] = parse_descriptions(brief_description, description)

                # Extract schedule
                paragraphs = dom.xpath('//*[@id="content"]/section[1]/div/div/div/div/div/div[2]/article/div[3]/section[2]')[0]
                schedule = parse_paragraphs(paragraphs)
                events[i]['additionalInformation'] = schedule

                # Extract venue/ mode
                paragraphs = dom.xpath('//*[@id="content"]/section[1]/div/div/div/header/div[3]/div/div[1]/div/div[2]')[0]
                location = parse_paragraphs(paragraphs)
                events[i]['location'] = location
                events[i]['mode'] = get_mode_from_location(location)
                if PRINT_MODE == 3 : print(f"scrape_innovate(): Successfully added event.")
                break
            else:
                if PRINT_MODE >= 2 : print(f"scrape_innovate(): Connection unsuccessful.\nError: {response.status_code} - {response.text}")
                if DEBUG_MODE : debug_mode_input()
                if PRINT_MODE >= 2 : print(f"scrape_innovate(): Retrying in 10 seconds")
                time.sleep(10)
    if PRINT_MODE == 3 : print(f"scrape_innovate(): Cordy information added. Now classifying and filtering events.") 
    return list(classify(events))

# (3) ---------------------- MAIN FUNCTIONS ----------------------

def scrape(print_mode='Off', debug_mode=False, return_data=False):
    # quite_mode has 3 options:
    #   (1) off
    #   (2) critical
    #   (3) all
    # debug_mode:
    #   Pass in True to enable user inputs for decisions
    # return_data:
    #   Pass in True to enable returning the list of JSON after scraping
    #   Else, the scraped data will be inserted into the database.
    global PRINT_MODE
    global DEBUG_MODE
    match print_mode:
        case 'critical':
            print("scrape(): Print mode set to: Critical")
            PRINT_MODE = 2
        case 'all':
            print("scrape(): Print mode set to: All")
            PRINT_MODE = 3
        case _:
            PRINT_MODE = 1
    DEBUG_MODE = debug_mode if (debug_mode == True) else False
    if PRINT_MODE >= 2 : print(f"scrape(): Debug mode set to {str(DEBUG_MODE)}.")
    cordy_data = scrape_cordy()
    sginnovate_data = scrape_innovate()
    if PRINT_MODE == 3 : print(f"scrape(): Scraping completed.")
    data = list(cordy_data) + list(sginnovate_data)
    try:
        with open('output.json', 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass


    if return_data:
        if PRINT_MODE == 3 : print(f"scrape(): Returning data.")
        return data
    else:
        if PRINT_MODE == 3 : print(f"scrape(): Inserting data into database.")
        insert_to_database(data)
        if PRINT_MODE == 3 : print(f"scrape(): Insert successful.")
    

# (4) ---------------------- SAMPLE RUN CODE ----------------------
# if __name__ == "__main__":
#     # Testing Code / Sample use for code
#     # data = scrape()                                  # To run in background
#     data = scrape(print_mode="all", debug_mode=True) # To run with debugging
#     # To save data locally
#     with open('output.json', 'w') as f:
#         json.dump(data, f, indent=2, ensure_ascii=False)

    # with open('./services/output.json', 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    # for j in data:
    #     # change signupdeadline to none
    #     # change date to signupdeadline
    #     # try:
    #     #     j['signupDeadline'] = j['date']
    #     #     j.pop('date', None)
    #     # except:
    #     #     pass
    #     # try:
    #     #     if j['signupDeadline'] == '':
    #     #         j['signupDeadline'] = None
    #     # except:
    #     #     pass
    # insert_to_database(data)

    # data = scrape(print_mode="all", return_data=True)
    # try:
    #     with open('output.json', 'w', encoding="utf-8") as f:
    #         json.dump(data, f, indent=2, ensure_ascii=False)
    # except:
    #     pass
    # insert_to_database(data)