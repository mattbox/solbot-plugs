# -*- coding: utf-8 -*-
"""
=================================================
:mod:`onebot.plugins.weather` Weather plugin
=================================================

Basic plugin for displaying the weather

 “Powered by Dark Sky” - https://darksky.net/poweredby/.
"""
import asyncio
import datetime
import re

import geocoder
import requests
from darksky import DarkSky
from time import strftime

import irc3
from irc3.plugins.command import command


@irc3.plugin
class WeatherPlugin(object):
    """Plugin to provide:

    * Weather Plugin
    """
    requires = [
        'irc3.plugins.command',
        'onebot.plugins.users'
    ]

    def __init__(self, bot):
        """Initialize the plugin"""
        self.bot = bot
        self.log = bot.log.getChild(__name__)
        self.config = bot.config.get(__name__, {})
        try:
            self.api_key = self.config['api_key']
        except KeyError:
            raise Exception(
                "You need to set the DarkSky.net api_key"
                "in the config section [{}]".format(__name__))

    @command
    def w(self, mask, target, args):
        """Gives basic weather information for the user
            %%w [<location>]...
        """
        if target == self.bot.nick:
            target = mask.nick

        @asyncio.coroutine
        def wrap():
            response = yield from self.w_response(mask, args)
            self.log.debug(response)
            self.bot.privmsg(target, response)
        asyncio.async(wrap())

    @asyncio.coroutine
    def w_response(self, mask, args):
        """Returns appropriate reponse to w request"""
        local = args['<location>'] #searchable string
        location = yield from self.get_local(mask.nick)

        if not local and not location:
            response = "Sorry, I don't remember where you are"
            return response
        elif local:
            try:
                location = yield from self.get_geo(mask.nick, args)
            except ConnectionError as status:
                response = "Sorry, I could't find that place - " + str(status)
                return response
            self.set_local(mask.nick, geo) # remember args when given

        try:
            self.ds = DarkSky(location[:2])
        except (requests.exceptions.Timeout,
                requests.exceptions.TooManyRedirects,
                requests.exceptions.RequestException,
                requests.exceptions.HTTPError,
                ValueError, KeyError)as errmsg:
            return str(errmsg)

        summary = self.ds.forecast.currently.summary
        temp = self.ds.forecast.currently.temperature
        if self.ds.forecast.flags.units == "us":
            deg = "F"
        else:
            deg = "C"
        response = "{0} - {1}, {2}\u00B0{3}".format(
            location[2], summary, temperature, deg)
        return response

# Set the api key using the system's environmental variables.
# $ export GOOGLE_API_KEY=<Secret API Key>
    @asyncio.coroutine
    def get_geo(self, mask, args):
    """Gets the geographical information from Google Geocoding,
    returns [latitude,longitude,"city"]
    """
        local = ' '.join(args['<location>'])
        geo = geocoder.google(local)

        if geo.status == "OK":
            location = geo.latlng
            if (geo.city, geo.state):
                location.append("{0}, {1}".format(geo.city, geo.state))
            else:
                location.append(geo.country)
            return location
        else:
            self.log.info("Geocode error for {0} - {1}".format(mask.nick,
                geo.status))
            raise ConnectionError(geo.status)

    def set_local(self, mask, location):
        """Stores the location of the user as a list of
        [longitude, latitude, "city name"]
        """
        self.log.info("Storing location {0} for {1}".format(location, mask.nick))
        self.bot.get_user(mask.nick).set_setting('location', location)
        #self.bot.privmsg(target, "Got it.")

    @asyncio.coroutine
    def get_local(self, nick):
        """Gets the location, associated with a user from the database.
        If user is not in the database, returns None.
        """
        user = self.bot.get_user(nick)
        result = yield from user.get_setting('location', nick)
        return result

#NOTE this isn't currently being used
def _unixformat(unixtime,Date=False):
    """Turns Unix Time into something readable

    "9:34 PM (08/24/16)"
    """
    time = datetime.datetime.fromtimestamp(
        int(unixtime)).strftime("%I:%M %p")

    date = datetime.datetime.fromtimestamp(
        int(unixtime)).strftime(" (%m/%d/%y)")
    if Date:
        return time + date
    else:
        return time
