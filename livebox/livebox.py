#!/usr/bin/env python3
# -*- coding: utf8 -*-

# This file is a part of Livebox_tools
#
# Copyright (c) 2015 Pierre GINDRAUD
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Livebox Tools

This file provide some tools to use new Livebox 3 Firmware (Soft At Home) API
"""

import urllib.parse
import http.client
from http.client import *
import json
import getpass


class Livebox:
  """This is the main API requester class
  """

  PASSWORD = ""
  USERNAME = "admin"
  URL_P_AUTH = "/authenticate?username={username}&password={password}"
  URL_P_LOGOUT = "/logout"

  def __init__(self, protocol='http', host='livebox'):
    """ Build a Livebox API client

    @param[in] proto : the http protocol to use (http, https)
    @parma[in] host : the domain name of the target livebox host
    """
    self.__protocol = protocol
    self.__host = host
    self.__port = http.client.HTTP_PORT
    self.base_url = "{:s}://{:s}".format(protocol, host)

    self.__connection = None
    self.__cookies = ""
    self.__contextID = ""
    self.__is_connected = False

# AUTHENTIFICATION SECTION

  def login(self, password=None):
    """Authenticate to Livebox host

    This function try to perform a full Authenticate procedure
    to the livebox host

    @param[in] password : is provided the password to use as credential
          if not provided use PASSWORD class attribute if available
          if not of them are available the password is asked to user
    """
    if password is None:
      if Livebox.PASSWORD:
        password = Livebox.PASSWORD
      else:
        password = getpass.getpass()

    values = {'username': 'admin',
              'password': password}

    response = self.__query(Livebox.URL_P_AUTH.format(**values),
                            urllib.parse.urlencode(values).encode('utf8'))
    if response is not None and response.status == http.client.OK:
      datas = json.loads(response.read().decode('utf8'))
      # save connection parameters
      self.__contextID = datas['data']['contextID']
      self.__cookies_code = response.info()['Set-Cookie'].split('/')[0]
      self.__cookies = (
          response.info()['Set-Cookie'].split(';')[0] + "; " +
          self.__cookies_code + "/login=" + values['username'] + "; " +
          self.__cookies_code + "/context=" + self.__contextID)

      self.__is_connected = True

  def logout(self):
    """Logout from Livebox host

    Make a logout query to livebox
    """
    if not self.__is_connected:
      return
    response = self._queryAuth(Livebox.URL_P_LOGOUT)
    self.__is_connected = False

# QUERY SECTION
  def __url(self, query):
    """Compute the full URL from query string

    @param[in] query : the query part of the url
    @return [string] the full url with proto+host+query
    """
    return self.base_url + query

  def __query(self, query, params='', headers=dict(),
              content_type='application/json',
              method='POST'):
    """Make a basic HTTP query to host

    @param[in] query : the query string (part after / in URL)
    @param[in] params OPTIONNAL : the data (body) of the query
    @param[in] headers OPTIONNAL : the additionnal headers to put in the query
    @param[in] content_type OPTIONNAL : type of content to request to host
    @param[in] method OPTIONNAL : the type of http method
    @return HTTPResponse if query success, None otherwise
    """
    if isinstance(params, str):
      data = params.encode('utf8')
    else:
      data = params

    if self.__connection is None:
      self.__connection = http.client.HTTPConnection(self.__host,
                                                     self.__port)

    headers['Connection'] = 'keep-alive'
    headers['User-Agent'] = 'Python Livebox Tools'
    if 'Content-Type' not in headers:
      headers['Content-Type'] = content_type

    try:
      self.__connection.request(method, query, data, headers)
      response = self.__connection.getresponse()
    except NotConnected as e:
      print('Error not connected')
      return None
    except InvalidURL as e:
      print('Error InvalidURL')
      return None
    except BadStatusLine as e:
      print('Error BadStatusLine')
      return None
    except ImproperConnectionState as e:
      print('Error ImproperConnectionState')
      return None
    except HTTPException as e:
      print('Error HTTP')
      return None
    return response

  def _queryUnauth(self, query, params='', method='POST'):
    """Execute a simple query without any specific headers

    @param[in] query : the query string (part after / in URL)
    @param[in] params OPTIONNAL : the data (body) of the query
    @param[in] method OPTIONNAL : the type of http method
    @return A dict which contains JSON response datas or empty str
    """
    response = self.__query(query, params, method=method)
    if not response:
      return ""
    r_data = response.read() 
    if r_data:
      return json.loads(r_data.decode('utf8'))
    else:
      return ""

  def _queryAuth(self, query, params='', headers=dict(), method='POST'):
    """Execute a query with authentication specific headers

    @param[in] query : the query string (part after / in URL)
    @param[in] params OPTIONNAL : the data (body) of the query
    @param[in] headers OPTIONNAL : the additionnal headers to put in the query
    @param[in] method OPTIONNAL : the type of http method
    @return A dict which contains JSON response datas or empty str
    """
    headers['Cookie'] = self.__cookies
    headers['X-Context'] = self.__contextID
    headers['X-Sah-Request-Type'] = 'idle'
    headers['X-Requested-With'] = 'XMLHttpRequest'
    headers['X-Prototype-Version'] = '1.7'
    headers['DNT'] = '1'

    response = self.__query(query, params, headers, method=method)
    if not response:
      return ""
    r_data = response.read()
    r_header = dict(response.getheaders())
    if r_data and r_header['Content-Type'].split(';')[0] == 'application/json':
      return json.loads(r_data.decode('utf8'))
    else:
      return ""

  def _sysbus(self, quest, param='{"parameters":{}}',
              auth=False,
              method='POST'):
    """Execute a SYSBUS call on the host

    @param[in] quest : the query object in string format
    @param[in] params OPTIONNAL : the data (body) of the query
    @param[in] auth OPTIONNAL : a boolean that indicated if the query must be
              executed as authenticated
    @param[in] method OPTIONNAL : the type of http method
    """
    if auth:
      return self._queryAuth("/sysbus/{:s}".format(quest), param,
                             method=method)
    else:
      return self._queryUnauth("/sysbus/{:s}".format(quest), param,
                               method=method)

  def require_auth(func):
    """ Apply this decorator to all method that require to be authentified
    This decorator put a basic verification to check that given method is call
    in a authenticated environnement
    """
    def check_auth(*args, **kwargs):
      """Check if the current connection s authenticated on the host or not

      If not authenticated return empty string
      """
      if isinstance(args[0], Livebox) and args[0].__is_connected:
        return func(*args, **kwargs)
      else:
        return "AUTH NEEDED"
    return check_auth
    
  def action(func):
    """ Apply this decorator to all method that cause physical action on LB
    """
    def check_action(*args, **kwargs):
      """Show a message on action command
      """
      print('ACTION')
      return func(*args, **kwargs)
    return check_action



def print_r(content, align=''):
  """ Show a JSON array into a more visual form

  Use this as debug
  """
  if isinstance(content, dict):
    for key in content:
      head = align + str(key) + " => "
      print(head)
      print_r(content[key], ' '*len(head))
  elif isinstance(content, list):
    for val in content:
      print_r(val, ' '*len(align))
  else:
    value = str(content)
    if value:
      print(align + value)




if __name__ == '__main__':
  lb = Livebox()
  lb.login()

  lb.logout()
  
  
  
  