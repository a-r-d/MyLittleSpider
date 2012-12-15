#!/usr/bin/python
#
#   MyLittleSpider - a little, simple web crawler.
#   Aaron Decker - me@a-r-d.me
#   MIT License
#
#####################################################
#
#   To Do:
#       1. Parametize opts.
#       2. Speed up the RE thing.
#       3. Multi-Threading.
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

from bs4 import BeautifulSoup

#####################################################

SAVE_PAGES = True
SAVE_PAGES_TEXT_ONLY = True # removes all markup, does tags.strings to get text.
PROCESS_RE_AND_SAVE = True
SAVE_PAGE_DIR = "spider_results"
SCAN_TIME = str(int(time.time())) # want like- 1355284655
BASE_DIR = os.path.join(SAVE_PAGE_DIR, SCAN_TIME)
STATS_FILES = BASE_DIR

d = os.path.join(os.getcwd(), BASE_DIR)
if not os.path.exists(d):
    os.makedirs(d)

VERBOSITY = 2 ### 0, 1, 2, 3
"""
Verbosity explained:
    0 = no printing, except for exceptions
    1 = only important messages counts, ext.
    2 = frequent updates on the control flow of program.
    3 = prints out very many updates.
"""
SEEDS = [
    "http://a-r-d.me",
    "http://www.reddit.com/r/Programming",
    "http://news.ycombinator.com/"
    ]
RECURSION_LEVEL = 0

ALL_SCANNED_LINKS = []
PREVIOUS_LINK_SET = []
NEXT_LINK_SET = []

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
    "#" #idc about same page section links
    ] #contains- ignore files
REMOVE_FROM_URL = ["/","?","=","!",":",".",","]

RE_DICT = {
    'email_simple':r'.+\s+([\S]+@[\S]+)\s+.+',
    'phone_num_full_dot_or_dash':r'.+\s+([0-9]{3}[\.-][0-9]{3}[\.-][0-9]{4})\s+.+'
}

def harvest_content_by_expression(txt, url):
    if VERBOSITY > 1:
        print "Entering the RE checker for ", url
    try:
        total_matches = 0
        for key, value in RE_DICT.iteritems(): 
            if VERBOSITY > 2:
                print "checking RE: ", value
            captures = re.findall(value, txt)
            if VERBOSITY > 2:
                print "Matches: ", captures
            try:
                if captures != None and len(captures) > 0:
                    total_matches += len(captures)
                    f = open(os.path.join(STATS_FILES, "RE_harvest_" + key + ".txt"), 'a')
                    for c in captures:
                        if len(c) > 100:
                            continue # long stuff is prob. a false positive
                        f.write("%s: %s\n" % (url,c));
                    f.close()
                    
            except Exception, e:
                print "FAILED to save re results: ",url, e
        if VERBOSITY > 1:
            print "Num RE captures from page: ", total_matches
    except Exception, e:
        print "Failed re check on page- ",url, e


def get_all_links(txt):
    try:
        if VERBOSITY > 1:
            print "Size of page pulled: ", len(txt) / 1000, " kb"
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
        if VERBOSITY > 1:
            print "Found %s links from the page" % (len(urls))
            
        # no dupes:
        link_set = set(urls)
        link_list = list(link_set)
        return link_set
    except Exception, e:
        print "failed getting links - error: %s" % (e)
        return []


def get_page(url):
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'my lil spider (bot) v0.1')    
        response = urllib2.urlopen(req)
        the_page = response.read()
        if VERBOSITY > 1:
            if the_page == "":
                print "The page was blank at %s" % url
            else:
                print "The page length was: %s at %s" % (len(the_page), url)
        if SAVE_PAGES:
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
                if VERBOSITY > 1:
                    print "Saving file to: ", dir    
                f = open(dir, 'w')
                if SAVE_PAGES_TEXT_ONLY:
                    soupy = BeautifulSoup(the_page)
                    for s in soupy.stripped_strings:
                        f.write("%s\n" % s)
                else:
                    f.write(the_page)
                f.close()
            except Exception, e:
                print "FAILED TO SAVE PAGE: %s __ %s" % (url, e)
        return the_page
    except Exception, e:
        print "Failed on url %s, error- %s" % (url,e)
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
        if VERBOSITY > 2:
            print "The complete links before fixing:"
            print complete_links
    except Exception, e:
        print "Failed to check for http:// ", e
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
                if VERBOSITY > 2:
                    print "Corrected partial link: ", full_link
                complete_links.append(full_link)
            except:
                continue
        return complete_links
    except Exception, e:
        print "Failed on the link fixing for- %s, %s" % (base, e)
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
        if VERBOSITY > 1:
            diff = len(url_list) - len(cleaned)
            print "There %s duplicates that were filtered out." % diff
        return cleaned
    except Exception, e:
        print "Errored out on filtering the base- ", e
        return [] # dont want to get into a loop!
        
def single_harvest(url):
    try:
        if VERBOSITY > 0:
            print "pulling page @ %s" % url
        txt = get_page(url)
        if VERBOSITY > 0:
            print "Getting links from @ %s" % url 
        if PROCESS_RE_AND_SAVE:
            harvest_content_by_expression(txt, url)
        links = get_all_links(txt)
        if VERBOSITY > 0:
            print "Fixing partial links for %s" % url
        links = fix_partial_links(url, links)
        if VERBOSITY > 0:
            print "Filtering out the base on the links: "
        links = filter_out_base(url, links)
        if VERBOSITY > 1:
            print "Printing links from url: %s" % url 
            print "There were %s good links." % len(links)
            if VERBOSITY > 2:
                for l in links:
                    print l
        return links
    except Exception, e:
        print "Harvesting failed from: %s, %s" % (url,e)
        return []

#record scanned link:
def record_scanned_link(url):
    try:
        f = open(os.path.join(STATS_FILES, "visited_links.txt"), 'a')
        f.write("%s\n" % url)
        f.close()
    except Exception, e:
        print "Failed to write url to file %s / %s" % (url, e)
        
def record_harvested_links(url_list):
    try:
        f = open(os.path.join(STATS_FILES, "all_harvested_links.txt"), 'a')
        for url in url_list:
            f.write("%s\n" % url)
        f.close()
    except Exception, e:
        print "Failed to write url to file %s / %s" % (url, e)

#passed single full URL
def harvest_links_no_depth(url):
    t1 = time.time()
    res = single_harvest(url)
    t2 = time.time()
    diff = str(t2 - t1)
    if VERBOSITY > 1:
        print "Time on the call: %s seconds" % diff
    #remove dupes:
    link_set = set(res)
    link_list = list(link_set)
    return link_list #a list of links
        
def harvest_links_recursively(seed_list, depth):
    global ALL_SCANNED_LINKS
    global PREVIOUS_LINK_SET
    global NEXT_LINK_SET
    global BASE_DIR # the base dir needs to be opened 
    
    depth_count = 0
    if VERBOSITY > 0:
        print "Begining recursive harvester. Depth = %s" % depth
    while(depth_count < depth):
        if VERBOSITY > 0:
            print "Recursive depth: %s " % depth_count
        if depth_count == 0:
            for s in seed_list:
                links = []
                links = harvest_links_no_depth(s)
                ALL_SCANNED_LINKS.append(s)
                record_scanned_link(s)# write the visited link to this file
                record_harvested_links(links)# write all the links to this file
                if VERBOSITY > 2:
                    print "Number Links from the harvest- depth=0 ", len(links)
                if links != None:
                    NEXT_LINK_SET.extend(links) #
                
                if VERBOSITY > 1:
                    "NEXT_LINK_SET size: ", len(NEXT_LINK_SET)
                
        else:
            # get all of these links for the next set:
            BASE_DIR = os.path.join(BASE_DIR, str(depth_count)) #file writing should make a tree to mimic the control flow
            if not os.path.exists(BASE_DIR):
                os.makedirs(BASE_DIR)
            temp_link_set = []
            for link in NEXT_LINK_SET:
                if link not in ALL_SCANNED_LINKS:
                    links = harvest_links_no_depth(link)
                    record_scanned_link(link)# write the visited link to this file
                    record_harvested_links(temp_link_set)# write all the links to this file
                    ALL_SCANNED_LINKS.append(link) # make absolutely sure we do nothing twice.
                    temp_link_set.extend(links)
            # clear the old list, 
            if VERBOSITY > 0:
                print "Last list size: ", len(NEXT_LINK_SET)
                print "Next list size: ", len(temp_link_set)
            NEXT_LINK_SET = []
            NEXT_LINK_SET.extend(temp_link_set)
            PREVIOUS_LINK_SET = []
            PREVIOUS_LINK_SET.extend(NEXT_LINK_SET)
                
        depth_count += 1
        
        
def main():
    #harvest_links_no_depth(SEEDS[0])
    harvest_links_recursively(SEEDS, 3)

if __name__ == '__main__':
    main()
