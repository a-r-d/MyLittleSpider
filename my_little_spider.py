#!/usr/bin/python
#
#   MyLittleSpider - a little, simple web crawler.
#   Aaron Decker - me@a-r-d.me
#   MIT License
#
import urllib
import urllib2
import socket
import time
import random
import datetime
import os

from bs4 import BeautifulSoup

#####################################################

SAVE_PAGES = True
SAVE_PAGE_DIR = "spider_results"
SCAN_TIME = str(int(time.time())) # want like- 1355284655
BASE_DIR = os.path.join(SAVE_PAGE_DIR, SCAN_TIME)

if SAVE_PAGES:
    d = os.path.join(os.getcwd(), BASE_DIR)
    if not os.path.exists(d):
        os.makedirs(d)

VERBOSITY = 2 ### 0, 1, 2, 3
"""
Verbosity explained:
    0 = no printing.
    1 = only important messages counts, ext.
    2 = frequent updates on the control flow of program.
    3 = prints out very many updates.
"""
SEEDS = [
    "http://www.reddit.com/r/Programming/", 
    "http://slashdot.org/", 
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
    ".pdf"
    ] #contains- ignore files
REMOVE_FROM_URL = ["/","?","=","!",":",".",","]

def get_all_links(txt):
    try:
        if VERBOSITY > 1:
            print "Size of page pulled: ", len(txt) / 1000, " kb"
        urls = []
        soup = BeautifulSoup(txt)
        the_links = soup.find_all("a")
        
        for link in the_links:
            href = link.get("href")
            if href not in URL_FILTER_SET:
                for test in URL_FILTER_SET_CONTAINS:
                    if href != None:
                        if href.find(test) == -1 and href.find(test.upper()) == -1:
                            urls.append(href)
        if VERBOSITY > 1:
            print "Found %s links from the page" % (len(urls))
        return urls
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

#passed single full URL
def harvest_links_no_depth(url):
    t1 = time.time()
    res = single_harvest(url)
    t2 = time.time()
    diff = str(t2 - t1)
    if VERBOSITY > 1:
        print "Time on the call: %s seconds" % diff
    return res #a list of links
        
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