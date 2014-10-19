#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import urllib2
import logging
from xml.dom import minidom



from google.appengine.ext import db
from google.appengine.api import memcache

JINJA_ENVIRONMENT = jinja2.Environment(autoescape=True,
loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))




GMAPS_URL="http://maps.googleapis.com/maps/api/staticmap?size=580x363&sensor=false&"

def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' %(p.lat,p.lon)
                       for p in points)
    return GMAPS_URL + markers


IP_URL="http://api.hostip.info/?ip="

def get_coords(ip):
    #ip="4.2.2.2"
    ip="23.24.209.141"
    #ip="59.180.16.47"
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except urllib2.URLError:
        return


    if content:
        #parse the xml and find the coordinates
        x=minidom.parseString(content)
        coords=x.getElementsByTagName("gml:coordinates")
        if coords and coords[0].childNodes[0].nodeValue:
            #print coords
            long,lat = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat,long)



class Art(db.Model):
    title=db.StringProperty(required=True)
    art=db.TextProperty(required=True)
    created=db.DateTimeProperty(auto_now_add=True)
    coords=db.GeoPtProperty()
 

def top_arts(update =False):
    key='top'
    #if not update and key in CACHE:
     #   arts = CACHE[key]
    arts = memcache.get(key)
    if arts is None or update:
        logging.error("DB QUERY")
        arts=db.GqlQuery("SELECT * FROM Art ORDER BY created DESC limit 10")
        arts=list(arts)
        #CACHE[key] = arts
        memcache.set(key, arts)
    return arts


class MainHandler(webapp2.RequestHandler):
    
    def write(self,title="",art="",error=""):
        arts=top_arts()
        #arts=db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
        #results=arts.fetch(10)
        #for result in results:
            #result.delete()
        #db.delete(results)
    

        #prevent running of multiple queries
        arts=list(arts)


        #find which arts have coordinates
        #for a in arts:
            #if a.coords:
                #points.append(a.coords)
        points = filter( None , (a.coords for a in arts ))
        #self.response.out.write(repr(points))

        img_url = None
        if points:
            img_url=gmaps_img(points)

        template_values = {'title':title,
                            'art': art,
                            'error': error,
                            'arts': arts,
                            'img_url': img_url
                           }

        
        #self.render("form.html", title=title, art=art, error=error,arts=arts)
        template = JINJA_ENVIRONMENT.get_template('form.html')
        self.response.out.write(template.render(template_values))
    
        
    def get(self):
        self.response.out.write(self.request.remote_addr)
        #self.response.out.write(repr(get_coords(self.request.remote_addr)))
        self.write()


    def post(self):
        title=self.request.get("title")
        art=self.request.get("art")
        if title and art:
            a=Art(title=title,art=art)

            #look at the coordinates of the user from their ip
            #if coordinates available,add them to the art
            coords=get_coords(self.request.remote_addr)

            if coords:
                a.coords=coords


            
            a.put()
            top_arts(True)
            self.redirect("/")

        else:
            error="enter both title and art"
            self.write(title,art,error)
    

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
