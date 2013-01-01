#!/usr/bin/python
#
#   MyLittleSpider - a little, simple web crawler.
#   Aaron Decker - me@a-r-d.me
#   MIT License
#
#####################################################
#
#   To Do:
#       1. Parametize input opts.
#       2. Speed up the RE thing.
#
#####################################################
import urllib
import urllib2
import socket
import time
import random
import datetime
import os
import re
from threading import Thread, Lock, currentThread
from atexit import register

from bs4 import BeautifulSoup

#####################################################

## GLOBAL FLAGS:
DEBUG_MODE = True
SAVE_PAGES = True
SAVE_PAGES_TEXT_ONLY = True # removes all markup, does tags.strings to get text.
PROCESS_RE_AND_SAVE = False # this is really really slow. Don't use!

## GLOBAL VARS:
NUM_THREADS = 6
VERBOSITY = 0 ### 0, 1, 2, 3
"""
Verbosity explained:
    0 = no printing, except for exceptions
    1 = only important messages counts, ext.
    2 = frequent updates on the control flow of program.
    3 = prints out very many updates.
"""
SAVE_PAGE_DIR = "spider_results"
SCAN_TIME = str(int(time.time())) # want like- 1355284655
BASE_DIR = os.path.join(SAVE_PAGE_DIR, SCAN_TIME)
STATS_FILES = BASE_DIR
USER_AGENT = "MyLittleSpider (bot) 0.1"
SEEDS = [
    "http://a-r-d.me",
    "http://frameworkhell.com",
    ]
RECURSION_LEVEL = 3
ALL_SCANNED_LINKS = []
PREVIOUS_LINK_SET = []
NEXT_LINK_SET = [] 
TEMP_LINK_SET = []

## set up file write location
d = os.path.join(os.getcwd(), BASE_DIR)
if not os.path.exists(d):
    os.makedirs(d)

## Global Constants
URL_FILTER_SET = [
    "",
    "#",
    "/",
    "javascript:void(0)"
    ] #is = to
URL_FILTER_SET_CONTAINS = [
    ".jpg",
    ".gif",
    ".png",
    ".txt",
    ".zip", 
    ".exe",
    ".js",
    ".css",
    ".pdf",
    ".ipa",
    ".apk",
    ".rar",
    ".tar.gz",
    ".jar",
    ".7z",
    ".plist",
    "#" #idc about same page section links
    ] #contains- ignore files
REMOVE_FROM_URL = ["/","?","=","!",":",".",","]
RE_DICT = {
    'email_simple':r'.+\s+([\S]+@[\S]+)\s+.+',
    'phone_num_full_dot_or_dash':r'.+\s+([0-9]{3}[\.-][0-9]{3}[\.-][0-9]{4})\s+.+'
}

######################################
## Threading work:
#######################################
visited_lock = Lock()
print_lock = Lock()
shared_file_write_lock = Lock()

###################################################
###################################################

def smart_print(level, txt):
    if VERBOSITY > level:
        print_lock.acquire()
        thread_name = currentThread().name
        print thread_name, ": ", txt
        print_lock.release()
def smart_print_list(level, printing):
    if VERBOSITY > level:
        print_lock.acquire()
        for p in printing:
            print p
        print_lock.release()

def harvest_content_by_expression(txt, url):
    smart_print(1, "Entering the RE checker for %s" % url)
    try:
        total_matches = 0
        for key, value in RE_DICT.iteritems(): 
            smart_print(2, "checking RE: %s" % value)
            captures = re.findall(value, txt)
            smart_print(2, "Matches: %s" % captures)
            try:
                shared_file_write_lock.acquire()
                if captures != None and len(captures) > 0:
                    total_matches += len(captures)
                    ## Lock for shared file writing:
                    f = open(os.path.join(STATS_FILES, "RE_harvest_" + key + ".txt"), 'a')
                    for c in captures:
                        if len(c) > 100:
                            continue # long stuff is prob. a false positive
                        f.write("%s: %s\n" % (url,c));
                    f.close()
            except Exception, e:
                smart_print(-1, "FAILED to save re results: %s %s" % (url, e))
            finally:
                shared_file_write_lock.release()
        smart_print(1, "Num RE captures from page: %s" % total_matches)
    except Exception, e:
        smart_print(-1, "Failed re check on page- %s %s" % (url, e))


def get_all_links(txt):
    try:
        kb = str(len(txt) / 1000) + " kb"
        smart_print(1, "Size of page pulled: %s" % kb)
        urls = []
        soup = BeautifulSoup(txt)
        the_links = soup.find_all("a")
        
        for link in the_links:
            href = link.get("href")
            if href not in URL_FILTER_SET and href != None:
                bad = False
                for test in URL_FILTER_SET_CONTAINS:
                    if href.find(test) != -1 or href.find(test.upper()) != -1:
                        bad = True
                        break
                if not bad:
                    urls.append(href)
        smart_print(1, "Found %s links from the page" % (len(urls)))
        # no dupes:
        link_set = set(urls)
        link_list = list(link_set)
        return link_set
    except Exception, e:
        smart_print(-1, "failed getting links - error: %s" % (e))
        return []


def get_page(url):
    try:
        ## actual page request:
        req = urllib2.Request(url)
        req.add_header('User-Agent', USER_AGENT)    
        response = urllib2.urlopen(req)
        the_page = response.read()
        
        if VERBOSITY > 1:
            if the_page == "":
                smart_print(1,  "The page was blank at %s" % url)
            else:
                smart_print(1, "The page length was: %s at %s" % (len(the_page), url))
        if SAVE_PAGES:
            # this should never be getting same URL- so DONT NEED TO LOCK!
            # pages are saved- we can will write in the directory listed:
            try:
                # something like:
                # /home/user/scans/1355284655/http-__reddit.com__.txt
                url_name = url
                for char in REMOVE_FROM_URL:
                    url_name = url_name.replace(char, "-") #replace for the file system
                #dir = os.path.join(os.getcwd(), SAVE_PAGE_DIR, SCAN_TIME, url_name, "__.txt")
                dir = os.path.join(os.getcwd(), BASE_DIR, url_name + "_.txt")
                #windows file size length issues.
                if len(dir) > 255:
                    over_by = len(dir) - 255
                    fname_len = len(url_name + "_.txt")
                    base_len = len(s.path.join(os.getcwd(), BASE_DIR))
                    shorten_to = fname_len - over_by
                    dir = dir[-shorten_to:] # shorten to the last whatever
                smart_print(1, "Saving file to: %s" % dir )
                f = open(dir, 'w')
                if SAVE_PAGES_TEXT_ONLY:
                    soupy = BeautifulSoup(the_page)
                    for s in soupy.stripped_strings:
                        output = "%s\n" % s
                        f.write(output.encode('utf-8'))
                else:
                    f.write(the_page)
                f.close()
            except Exception, e:
               smart_print(-1, "FAILED TO SAVE PAGE: %s __ %s" % (url, e))
        return the_page
    except Exception, e:
        smart_print(-1, "Failed on url %s, error- %s" % (url,e))
        return "" #if we return empty string, that signals failure.

        
def fix_partial_links(base, url_list):
    partials = []
    complete_links = []
    try:
        for l in url_list:
            if l != None:
                if l.find("http://") == -1:
                    partials.append(l)
                else:
                    complete_links.append(l)
        smart_print(2, "The complete links before fixing:")
        smart_print_list(2, complete_links)
    except Exception, e:
        smart_print(-1, "Failed to check for http:// %s" % e)
        return url_list
            
    try:
        for p in partials:
            #this just needs the base appended onto the front:
            try:
                full_link = ""
                if base[-1] == "/" and p[0] == "/":
                    full_link = base[:-1] + p #substring all but the last on the base
                elif base[-1] == "/" and p[0] != "/":
                    full_link = base + p
                elif base[-1] != "/" and p[0] == "/":
                    full_link = base + p
                elif base[-1] != "/" and p[0] != "/":
                    full_link = base + "/" + p
                smart_print(2, "Corrected partial link: %s" % full_link);
                complete_links.append(full_link)
            except:
                continue
        return complete_links
    except Exception, e:
        smart_print(-1, "Failed on the link fixing for- %s, %s" % (base, e))
        return complete_links

def filter_out_base(base, url_list):
    try:
        cleaned = []
        for l in url_list:
            if len(l) > 1 and l not in URL_FILTER_SET:  
                if l == base:
                    continue
                elif l[:-1] == base: #do all but last, to remove trailing slash.
                    continue
                elif l == base[:-1]:
                    continue
                elif l[:-1] == base[:-1]:
                    continue
                else:
                    cleaned.append(l)
                    
        diff = len(url_list) - len(cleaned)    
        smart_print(1, "There %s duplicates that were filtered out." % diff)
        return cleaned
    except Exception, e:
        smart_print(-1, "Errored out on filtering the base- %s" % e)
        return [] # dont want to get into a loop!
        
def single_harvest(url):
    try:
        smart_print(0, "pulling page @ %s" % url)
        # locking: none required
        txt = get_page(url)
        smart_print(0,  "Getting links from @ %s" % url)
        # lock needed here- shared file:
        if PROCESS_RE_AND_SAVE:
            harvest_content_by_expression(txt, url)
        # locking: none required
        links = get_all_links(txt)
        smart_print(0, "Fixing partial links for %s" % url) 
        # locking: none required
        links = fix_partial_links(url, links)
        smart_print(0, "Filtering out the base on the links: ")
        # locking: none required
        links = filter_out_base(url, links)
        smart_print_list(1, [
            "Printing links from url: %s" % url,
            "There were %s good links." % len(links)
            ])
        smart_print_list(2, links)
        return links
    except Exception, e:
        smart_print(-1, "Harvesting failed from: %s, %s" % (url,e)) ## -1 ensures always print
        return []

#record scanned link:
def record_scanned_link(url):
    try:
        shared_file_write_lock.acquire()
        f = open(os.path.join(STATS_FILES, "visited_links.txt"), 'a')
        f.write("%s\n" % url)
        f.close()
    except Exception, e:
        smart_print(-1, "Failed to write url to file %s / %s" % (url, e))
    finally:
        shared_file_write_lock.release() 
        
def record_harvested_links(url_list):
    try:
        shared_file_write_lock.acquire()
        f = open(os.path.join(STATS_FILES, "all_harvested_links.txt"), 'a')
        for url in url_list:
            f.write("%s\n" % url)
        f.close()
    except Exception, e:
        smart_print(-1, "Failed to write url to file %s / %s" % (url, e))
    finally:
        shared_file_write_lock.release() 

#passed single full URL
def harvest_links_no_depth(url):
    t1 = time.time()
    res = single_harvest(url)
    t2 = time.time()
    diff = str(t2 - t1)
    smart_print(1, "Time on the call: %s seconds" % diff)
    #remove dupes:
    link_set = set(res)
    link_list = list(link_set)
    return link_list #a list of links
      

def thread_harvestor(links_for_you):
    global ALL_SCANNED_LINKS
    global TEMP_LINK_SET
    
    for link in links_for_you:
        ## get lock to do anything with this list!!
        visited_lock.acquire()
        ok = False
        if link not in ALL_SCANNED_LINKS:
            ok = True
            ## lock to record the new link, make sure it wont scan it twice
            ALL_SCANNED_LINKS.append(link)
        visited_lock.release()
        
        if ok:
            # this is ok. Only writes to single file for page.
            links = harvest_links_no_depth(link)
            # this locks in here for file writing:
            record_scanned_link(link)# write the visited link to this file
            #this locks to write the new links to file:
            record_harvested_links(links)
            #append these links to the temp set.
            TEMP_LINK_SET.extend(links)
        else:
            return
      
def harvest_links_recursively(seed_list, depth):
    global ALL_SCANNED_LINKS
    global PREVIOUS_LINK_SET
    global NEXT_LINK_SET
    global BASE_DIR # the base dir needs to be opened 
    global TEMP_LINK_SET
    
    depth_count = 0
    smart_print(0, "Begining recursive harvester. Depth = %s" % depth)
    while(depth_count < depth):
        smart_print(0, "Recursive depth: %s " % depth_count)
        if depth_count == 0:
            for s in seed_list:
                links = []
                links = harvest_links_no_depth(s)
                ALL_SCANNED_LINKS.append(s)
                record_scanned_link(s)# write the visited link to this file
                record_harvested_links(links)# write all the links to this file
                
                smart_print(2, "Number Links from the harvest- depth=0 - %s" % len(links))
                if links != None:
                    NEXT_LINK_SET.extend(links) #
                
                smart_print(1, "NEXT_LINK_SET size: %s" % len(NEXT_LINK_SET))                    
        else:
            # get all of these links for the next set:
            BASE_DIR = os.path.join(BASE_DIR, str(depth_count)) #file writing should make a tree to mimic the control flow
            if not os.path.exists(BASE_DIR):
                os.makedirs(BASE_DIR)

            ## divide the next link set up evenly into total num of threads:
            thread_link_set = []
            for i in range(NUM_THREADS):
                thread_link_set.append([])
            for i in range(len(NEXT_LINK_SET)):
                thread_num = i % NUM_THREADS # eg if 4 threads- gives 0,1,2 or 3
                thread_link_set[thread_num].append(NEXT_LINK_SET[i])
            ## get a whole link set using threads:
            thread_container = []
            for i in range(NUM_THREADS):
                links_for_you = thread_link_set[i]
                t = Thread(target=thread_harvestor, args=(links_for_you,)) # no args requires:
                t.name = "thread %s" % i
                smart_print(-1, "Starting thread: %s / len list: %s" % (t.name, len(links_for_you)))
                t.start()
                thread_container.append(t)
            
            # join em. 
            for t in thread_container:
                t.join()
            
            #make sure we complete these threads before moving to next level:
            while True:
                num_alive = 0
                for t in thread_container:
                    if t.is_alive():
                        num_alive += 1
                if num_alive == 0:
                    smart_print(-1, "All threads dead, moving to next set")
                    break 
            # clear the old list, 
            smart_print_list(0, ["Last list size: %s" % len(NEXT_LINK_SET), 
                "Next list size: %s" % len(TEMP_LINK_SET)])        
            
            # cleanup after all threads complete at this level:
            NEXT_LINK_SET = []
            NEXT_LINK_SET.extend(TEMP_LINK_SET)
            PREVIOUS_LINK_SET = []
            PREVIOUS_LINK_SET.extend(NEXT_LINK_SET)
            TEMP_LINK_SET = []
            
            if DEBUG_MODE:
                wait = raw_input("Hit enter to move to next set (curr depth: %s)_" % depth_count )  
                
        depth_count += 1
        
        
def main():
    #harvest_links_no_depth(SEEDS[0])
    harvest_links_recursively(SEEDS, 5)

if __name__ == '__main__':
    main()
    
