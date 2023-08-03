"""Final Project for Advanced Programming in Python"""


import time
import os
try:
    # If running in Jupyter Notebook, install dependencies
    #get_ipython()  # Check if running in Jupyter Notebook
    os.system ("pip3 install slackclient==1.3.1 bs4 requests")
except NameError:
    print("Not running in Jupyter Notebook. Install deoendencies manually.\n pip3 install slackclient==1.3.1 bs4 requests")
    exit()

import requests
from slackclient import SlackClient
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

#Get slack bot token from environment variable or user input
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") or input("Enter your slack bot token: ")
general_channel = os.environ.get("GENERAL_CHANNEL_ID") or input("Enter the general channel id: ")
BOT_USER_ID = os.environ.get("BOT_USER_ID") or input("Enter the bot user id: ")

# Initialize slack client
slack_client = SlackClient(SLACK_BOT_TOKEN)

COURSE_DATA_KEYWORDS=keywords=["Section:", "Class No:", "Class Type:", "Enroll Stat:", "Open Seats:", "Open Restricted Seats:", "Wait List:","Meeting Day/Time/Location:"]
COURSE_TITLE_ID=["contentMain_lblSubject", "contentMain_lblCatNo", "contentMain_lblLongTitle"]

class Course(object):
    def __init__(self,course_num,section=None):
        self.error_log = []
        self.num = course_num
        self.sections = {}
        self.url = "https://www.lsa.umich.edu/cg/cg_detail.aspx?content=2270{}{}&termArray=w_20_2270".format(course_num,section if section else "001")
        resp = requests.get(self.url)
        soup = BeautifulSoup(resp.text, 'html.parser')

        try:
            self.title = " ".join(tltpart.string for tltpart in soup.find_all(id=COURSE_TITLE_ID))
        except Exception as error:
            self.error_log.append(error)
            print(str(error.__cause__))
            self.title = "Error parsing title"
        
        section_dict = {}
        for data in soup.find_all(string=COURSE_DATA_KEYWORDS)[1:]:
            try:
                values = list(data.parent.parent.stripped_strings)
                if values[0] == "Meeting Day/Time/Location:":
                    section_dict["Day:"] = values[1]
                    section_dict["Time:"] = values[2]
                    section_dict["Room:"] = values[3]
                    self.sections[section_dict["Section:"]] = section_dict
                    section_dict = {}
                elif len(values) > 1:
                    section_dict[values[0]] = values[1]    
                else:
                    section_dict[values[0]] = ""
            except Exception as error:
                self.error_log.append(error)
                #print(error)
    
    def open_sections_str(self):
        open_sections = {}
        for section_num, section_dict in self.sections.items():
            if section_dict["Enroll Stat:"] == "Open":
                open_sections[section_num] = section_dict
        return self.__str__(sections=open_sections)
    
    def __str__(self,sections=None):
        sections_to_output = sections or self.sections
        section_strings = []
        for section_dict in sections_to_output.values():
            section_strings.append("\n".join(key+ " " + value for key, value in section_dict.items()))
        if len(section_strings) > 0:
            return "\n" + self.title.center(58,"-") + "\n"+ "\n\n".join(section_strings)
        else:
            return None
            #return "" + ("No Open Sections for " + self.title).center(58,"-") + "\n"

    def __eq__(self,other):
        return self.title == other.title and self.sections == other.sections

class Search(object):
    def __init__(self, keyword=None,departments=None,instructor=None,course_levels=None,credits=None, \
                 dist_req=None, skills_req=None, day_pref=None, start_pref=None, end_pref=None, open_only=False):
        base_query="https://www.lsa.umich.edu/cg/cg_results.aspx?termArray=w_20_2270&cgtype=ug"
        self.open_only = open_only
        urls=[]
        urls.append(base_query)
        if keyword:
            urls[0] = self.url_add_param(urls[0],"keyword",keyword)
        if instructor:
            urls[0] = self.url_add_param(urls[0],"instr",instructor)
        if course_levels:
            urls[0] = self.url_add_param(urls[0],"numlvl",course_levels)
        if credits:
            urls[0] = self.url_add_param(urls[0],"credit",credits)
        if dist_req:
            urls[0] = self.url_add_param(urls[0],"dist",dist_req)
        if skills_req:
            urls[0] = self.url_add_param(urls[0],"reqs",skills_req)
        if day_pref:
            urls[0] = self.url_add_param(urls[0],"mp_day",day_pref)
        if start_pref:
            if " " not in start_pref:
                start_pref = start_pref[:-2] + " " + start_pref[-2:]    
            urls[0] = self.url_add_param(urls[0],"mp_starttime",start_pref)
        if end_pref:
            if " " not in end_pref:
                end_pref = end_pref[:-2] + " " + end_pref[-2:]    
            urls[0] = self.url_add_param(urls[0],"mp_endtime",end_pref)
        if departments:
            shared_url = urls[0]
            for url_num, department in enumerate(departments):
                if url_num > 0:
                    urls.append(shared_url)
                urls[url_num] = self.url_add_param(urls[url_num],"department",department)    
        self.urls = [url + "&show=1000" for url in urls]
        print(self.urls)
       
    
    def url_add_param(self,url,param_encoding,values):
        if type(values) is not list:
            values = [values]
        for value in values:
            url += "&{}={}".format(param_encoding,str(value).replace(" ","%20"))
        return url
    
    def find_course_nums(self,url):
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        course_nums = []
        
        for tag in soup.find_all():
            href = tag.get("href")
            if href and "cg_detail.aspx?content=2270" in href:
                course_num = href.replace("cg_detail.aspx?content=2270","") \
                                 .replace("&termArray=w_20_2270","")[:-3]
                if course_num not in course_nums:
                    course_nums.append(course_num)
        #print("Found courses: {}".format(",".join(course_num for course_num in course_nums)))
        return course_nums
    
    def get_course_nums(self):
        with ThreadPoolExecutor() as course_num_getter:
            for course_nums in course_num_getter.map(self.find_course_nums,self.urls):
                for course_num in course_nums:
                    yield course_num

    def get_course_objs(self):
        with ThreadPoolExecutor() as course_info_getter:
            yield from course_info_getter.map(Course,self.get_course_nums())

    def results(self,yield_strings=True):
        self._results = []
        for course in self.get_course_objs():
            if course and course not in self._results:
                self._results.append(course)
                if self.open_only:
                    if course.open_sections_str():
                        #print(course.open_sections_str())
                        if yield_strings:
                            yield course.open_sections_str()
                        else:
                            yield course
                else:
                    #print(course)
                    if yield_strings:
                        yield str(course)
                    else:
                        yield course
            
    def print_results(self):
        for course in self.results():
            print(course)
                
    def write_results(self,filename):
        with open(filename, "r+") as f:
            for course in self.results():
                f.write(str(course))


def get_departments():
    resp = requests.get("https://www.lsa.umich.edu/cg/cg_subjectlist.aspx?termArray=w_20_2270&cgtype=ug&allsections=true")
    soup = BeautifulSoup(resp.text,"html.parser")
    departments = []
    for i,a in enumerate(soup.find_all("a")):
        if i %2 !=0:
            departments.append(a.string)
    return departments[5:-1]


class Handler(object):
    def __init__(self,slack_client, command, channel, sender_id, thread_id, slackbot_state):
        self.slack_client = slack_client
        self.command = command.strip()
        self.channel = channel
        self.sender_id = sender_id
        self.thread_id = thread_id
        self.slackbot_state = slackbot_state
        
    
    def send_response_to_slack(self,response):
        send_to_slack(self.slack_client, self.channel, response, recipient = self.sender_id,thread_id=self.thread_id)
        return True
        
    def handle(self):
        response = "Not sure what you mean. Try something else, perhaps something that begins with *do*."
        return self.send_response_to_slack(response)

all_departments = get_departments()
search_words=["find", "search","look","classes","courses","class","course"]
class CourseSearch(Handler):
    def handle(self):
        command = [cmd.lower() for cmd in self.command.strip("?").split()]
        if any(word in command for word in search_words):
            params = {}
            params["departments"] = []
            for department in all_departments:
                if department.lower() in command:
                    params["departments"].append(department)
            
            if "level" in command:
                params["course_level"] = []
                for course_level in ["100","200","300","400","500"]:
                    if course_level in command:
                        params["course_level"].append(course_level)
            if "credit" in command or "credits" in command:
                params["credit_num"] = []
                for credit_num in ["1","2","3","4","5"]:
                    if credit_num in command:
                        params["credit_num"].append(credit_num)
            if "open" in command:
                params["open_only"] = True
                
            if "keyword" in command:
                params["keyword"] = ""
                quotes = False
                for c in self.command:
                    if c is '"':
                        quotes = not quotes
                    elif quotes:
                        params["keyword"] += c
            if "about" in command:
                params["keyword"] = command[command.index("about")+1].replace('"',"")
                        
            if "instructor" in command:
                params["instructor"]  = command[command.index("instructor")+1]
            if "professor" in command:
                params["instructor"]  = command[command.index("professor")+1] 
            
            if "at" in command:
                time_pref = self.parse_time(command,"at")
                params["start"] = time_pref 
                params["end"] = time_pref
            if "before" in command:
                params["end"] = self.parse_time(command,"before")
            if "after" in command:
                params["start"] = self.parse_time(command,"after")
            if "between" in command:
                params["start"] = self.parse_time(command, "between")
                params["end"] = self.parse_time(command, "and")
                
            if params["departments"] == [] and not params.get("keyword"):
                params["departments"] = all_departments
        
            self.send_response_to_slack("One sec I'm searching the LSA course guide for you...")
            
            
            s = Search(keyword=params.get("keyword"),departments=params.get("departments"), \
                       instructor=None,course_levels=params.get("course_level"),credits=params.get("credit_num"), \
                       dist_req=None, skills_req=None, day_pref=None, \
                       start_pref=params.get("start"), end_pref=params.get("end"), \
                       open_only=params.get("open_only",False))
            #response = "Here's what I found:\n"+ "\n".join(result for result in s.results() if "No Open Sections" not in result)
            
            for reply_num, course_str in enumerate(s.results()):
                if reply_num is 0:
                    course_str = "Here's what I found:\n"+course_str
                self.send_response_to_slack(course_str)
            return True
        return False
     
    def parse_time(self,command,specifier):
        all_times = {}
        for h in range(1,13):
            for m in ("A","P"):
                for f in ("",":00",":30","30"):
                    for s in (""," "):
                        hh = "3" if "3" in f else "0"
                        all_times["{}{}{}{}M".format(h,f,s,m)] = "{}:{}0 {}M".format(h,hh,m)
                        
        word_after = command[command.index(specifier)+1]
        if command[command.index(word_after)+1].upper() in ("AM", "PM"):
            word_after += command.index(word_after+1).upper()
        return all_times.get(word_after.upper()) 
        

def send_to_slack(slack_client, channel, text, recipient=None, thread_id=None):
    if recipient:
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            thread_ts=thread_id,
            text=mention(recipient) + " " + text,       
        )
    else:
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=text,       
        )



def extract_commands(events, user_id):
    if events:
        events_with_mentions = [event for event in events if message_to_id(event,user_id)]
        if events_with_mentions != []:
            return [(remove_mentions(e.get("text"),user_id),e.get("channel"),e.get("user"),e.get("ts")) for e in events_with_mentions]
    return []

def mention(slack_id):
    return "<@{}>".format(slack_id)
def remove_mentions(text,user_id=BOT_USER_ID,replace_str=""):
    return text.replace(mention(user_id),replace_str).strip()
def message_to_id(event, user_id=BOT_USER_ID):
    return event.get("type") == "message" and "subtype" not in event and mention(user_id) in event.get("text","")





state = {'speed':1,
        'menageries':{},
        'channel': "CR7NFJZAL"}

RTM_READ_DELAY = 1
def main(user_id=BOT_USER_ID, slackbot_state=state):
    slack_client.rtm_connect()
    botname = slack_client.api_call("auth.test")["user"]
    print("{} connected and running!".format(botname))
    searches_with_advisors = []
    search_queue = []
    max_searches = 1
    with ThreadPoolExecutor(max_workers=2*max_searches) as advisorBot:
        while True:
            for (command, channel, sender_id, thread_id) in extract_commands(slack_client.rtm_read(), BOT_USER_ID):
                print(command + " added to search queue")
                search = CourseSearch(slack_client, command, channel, sender_id, thread_id, slackbot_state)
                search_queue.append(search)

            for search, advisor in searches_with_advisors:
                print(advisor)
                if advisor.done():
                    search.send_response_to_slack("Your search is complete. Thanks for using AdvisorBot!")
                elif not advisor.running() and not advisor.done():
                    search.send_response_to_slack("An error occured with your search.\nTry asking AdvisorBot something like \"What math classes are open?\" or \"Find me an open 300 level english course\"")
                if not advisor.running():
                    searches_with_advisors.remove((search,advisor))
                
            while len(searches_with_advisors) <= max_searches and len(search_queue) > 0:
                next_search = search_queue.pop()
                print(next_search.command + " search started")
                searches_with_advisors.append((next_search,advisorBot.submit(next_search.handle)))

            
            print("{} search running... {} in queue".format(len(searches_with_advisors),len(search_queue)))
            time.sleep(RTM_READ_DELAY)

#print(Course("AAS111"))
main()
