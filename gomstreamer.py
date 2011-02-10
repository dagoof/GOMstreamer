# -*- coding: utf-8 -*-

'''
Copyright 2010 Simon Potter, Tomáš Heřman

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import urllib2
import cookielib
import urllib
import StringIO
import re
import os
import sys
from optparse import OptionParser
from string import Template
def main():

    global debug
    debug = False  # Set this to true to print debugging information

    # Application locations and parameters for different operating systems.
    # May require changing on OSX, can't test.
    vlcOSX = '/Applications/VLC.app/Contents/MacOS/VLC "--http-caching=$cache" "$url"'
    vlcLinux = 'vlc "--http-caching=$cache" "$url"'

    # Collecting options parsed in from the command line
    parser = OptionParser()
    parser.add_option("-p", "--password", dest = "password", help = "Password to your GOMtv account")
    parser.add_option("-e", "--email", dest = "email", help = "Email your GOMtv account uses")
    parser.add_option("-q", "--quality", dest = "quality", help = "Stream quality to use: 'HQ', 'SQ' or 'SQTest'. Default is 'SQTest'. This parameter is case sensitive.")
    parser.add_option("-c", "--command", dest = "command", help = "Custom command to run")
    parser.add_option("-d", "--buffer-time", dest = "cache", help = "Cache size in [ms]")

    # Setting default stream quality to 'SQTest'.
    parser.set_defaults(quality = "SQTest")

    # Determining which VLC command to use based on the OS that this script is being run on
    if os.name == 'posix' and os.uname()[0] == 'Darwin':
        parser.set_defaults(command = vlcOSX)
    else:
        parser.set_defaults(command = vlcLinux)  # On Windows, assuming VLC is in the PATH, this should work.

    parser.set_defaults(cache = 30000)  # Caching 30s by default
    (options, args) = parser.parse_args()

    # Printing out parameters
    if debug:
        print "Email: ", options.email
        print "Password: ", options.password
        print "Quality: ", options.quality
        print "Command: ", options.command

    # Stopping if email and password are defaults found in play.sh
    if options.email == "youremail@example.com" and options.password == "PASSWORD":
        print "Enter in your GOMtv email and password into play.sh."
        print "This script will not work correctly without a valid account."
        sys.exit(1)

    gomtvURL = "http://www.gomtv.net"
    gomtvLiveURL = gomtvURL + "/2011gslsponsors2/live/"
    gomtvSignInURL = gomtvURL + "/user/loginProcess.gom"
    values = {
             'cmd': 'login',
             'rememberme': '1',
             'mb_username': options.email,
             'mb_password': options.password
             }

    data = urllib.urlencode(values)
    cookiejar = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))

    # Signing into GOMTV
    request = urllib2.Request(gomtvSignInURL, data)
    urllib2.install_opener(opener)
    response = urllib2.urlopen(request)

    if len(cookiejar) == 0:
        print "Authentification failed. Please check your login and password."
        sys.exit(1)

    # Collecting data on the Live streaming page
    request = urllib2.Request(gomtvLiveURL)
    response = urllib2.urlopen(request)
    url = parseHTML(response.read(), options.quality)

    if debug:
        print "Printing URL on Live page:"
        print url
        print ""

    # Grab the response of the URL listed on the Live page for a stream
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    responseData = response.read()

    # Find out the URL found in the response
    url = parseStreamURL(responseData, options.quality)

    command = Template(options.command)
    commandArgs = {
                  'cache': options.cache,
                  'url': url
                  }
    cmd = command.substitute(commandArgs)
    cmd = cmd + " vlc://quit"

    print "Stream URL:", url
    print ""
    print "VLC command:", cmd
    print ""
    print "Playing stream via VLC..."
    os.system(cmd)

def parseHTML(response, quality):
    # Seeing what we've received from GOMtv
    if debug:
        print "Response:"
        print response

    # Parsing through the live page for a link to the gox XML file.
    # Quality is simply passed as a URL parameter e.g. HQ, SQ, SQTest
    try:
        patternHTML = r"http://www.gomtv.net/gox[^;]+;"
        urlFromHTML = re.search(patternHTML, response).group(0)
        urlFromHTML = re.sub(r"\" \+ playType \+ \"", quality, urlFromHTML)
        urlFromHTML = re.sub(r"\"[^;]+;", "", urlFromHTML)
    except AttributeError:
        print "Error: Unable to find the majority of the GOMtv XML URL on the Live page."
        sys.exit(0)

    # Finding the title of the stream, probably not necessary but
    # done for completeness
    try:
        patternTitle = r"this\.title[^;]+;"
        titleFromHTML = re.search(patternTitle, response).group(0)
        titleFromHTML = re.search(r"\"(.*)\"", titleFromHTML).group(0)
        titleFromHTML = re.sub(r"\"", "", titleFromHTML)
    except AttributeError:
        print "Error: Unable to find the stream title on the Live page."
        sys.exit(0)

    return (urlFromHTML + titleFromHTML)

def parseStreamURL(response, quality):
    # Observing the GOX XML file containing the stream link
    if debug:
        print "GOX XML:"
        print response

    # The response for the GOX XML if an incorrect stream quality is chosen is 1002.
    if (response == "1002"):
        print "Error: A premium ticket is required to watch higher quality streams, please choose 'SQTest' instead."
        sys.exit(0)

    # Grabbing the gomcmd URL
    try:
        streamPattern = r'<REF href="([^"]*)"/>'
        regexResult = re.search(streamPattern, response).group(1)
    except AttributeError:
        print "Error: Unable to find the gomcmd URL in the GOX XML file."
        sys.exit(0)

    # If we are using a premium ticket, we don't need to parse the URL further
    # we just need to clean it up a bit
    if quality == 'HQ' or quality == 'SQ':
        regexResult = urllib.unquote(regexResult) # Unquoting URL entities
        regexResult = re.sub(r'&amp;', '&', regexResult) # Removing amp;
        return regexResult

    # Collected the gomcmd URL, now need to extract the correct HTTP URL
    # from the string, only for 'SQTest'
    try:
        patternHTTP = r"(http%3[Aa].+)&quot;"
        regexResult = re.search(patternHTTP, regexResult).group(0)
        regexResult = urllib.unquote(regexResult) # Unquoting URL entities
        regexResult = re.sub(r'&amp;', '&', regexResult) # Removing amp;
        regexResult = re.sub(r'&quot;', '', regexResult) # Removing &quot;
    except AttributeError:
        print "Error: Unable to extract the HTTP stream from the gomcmd URL."
        sys.exit(0)

    return regexResult

# Actually run the script
if __name__ == "__main__":
    main()
