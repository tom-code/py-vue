import http.server
import socketserver
import socket
import time
import threading
import os
import fnmatch
import hashlib
import base64
import traceback
import struct


def sha1(inp):
  m = hashlib.sha1()
  m.update(inp.encode())
  return m.digest()

class WsChannel:
  def __init__(self, socket, name):
    self.socket = socket
    self.name = name

class Handler(http.server.SimpleHTTPRequestHandler):

  def do_GET(self):
    try:
      self.handl('get')
    except:
      traceback.print_exc()
      self.send_response(500)
      self.end_headers()

  def do_POST(self):
    self.handl('post')

  def log_message(self, format, *args):
    pass

  def ws_handle(self):
    while True:
      opc = self.rfile.read(1)
      if len(opc) == 0:
        break
      opcode = ord(opc) & 0xf

      leng = ord(self.rfile.read(1))
      mask = leng >> 7
      leng = leng & 0x7f
      if   leng == 126: leng = struct.unpack(">H", self.rfile.read(2))[0]
      elif leng == 127: leng = struct.unpack(">Q", self.rfile.read(8))[0]

      if mask != 0:
        msk = self.rfile.read(4)

      data = self.rfile.read(leng)
      data_dec = bytearray()
      if opcode == 1:    #data
        for i in range(leng):
          data_dec.append(data[i] ^ msk[i%4])
        data_dec = data_dec.decode('utf-8')
        print(data_dec)
      elif opcode == 8:  #close
        self.wfile.write(b'\x88\x00')
        break
      else:
        print('opcode {0}'.format(opcode))

  def ws_upgrade(self):
    key = self.headers['Sec-WebSocket-Key']
    sha = sha1( key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
    #self.close_connection = False
    #self.protocol_version = 'HTTP/1.1'
    self.send_response(101)
    self.send_header('Upgrade', 'websocket')
    self.send_header('Connection', 'upgrade')
    self.send_header('Sec-WebSocket-Protocol', '1')
    self.send_header('Sec-WebSocket-Accept', base64.b64encode(sha).decode())
    self.send_header('Content-Length', 0)
    self.end_headers()
    self.server.cons[self.request] = WsChannel(self.request, self.path)
    self.ws_handle()
    self.request.close()
    del self.server.cons[self.request]

  def handl(self, method):
    print(self.path)
    if self.path in self.server.redirect:
      self.send_response(301)
      self.send_header('Location', self.server.redirect[self.path])
      self.end_headers()
      return

    if self.path.startswith('/ws') and (self.headers['Upgrade'].lower() == 'websocket'):
      print('[httpd] websocket upgrade')
      self.ws_upgrade()
      return

    if self.path.startswith('/static'):
      fil = open(self.path.lstrip('/'), 'rb').read()
      self.send_response(200)
      self.end_headers()
      self.wfile.write(fil)
      return

    key = method + ' ' + self.path
    callback = None
    if key in self.server.handlers:
      callback = self.server.handlers[key]
    else:
      for h in self.server.handlers:
        if fnmatch.fnmatch(key, h):
          callback = self.server.handlers[h]

    if callback != None:
      self.send_response(200)
      self.end_headers()
      self.wfile.write(callback(self.path).encode('utf-8'))
    else:
      self.send_response(404)
      self.end_headers()

class MyTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
  def server_bind(self):
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.socket.bind(self.server_address)


class httpd:
  def __init__(self):
    pass
  def start(self, port):
    print('httpd listening on port {0}'.format(port))
    self.httpd = MyTCPServer(('', port), Handler)
    self.httpd.handlers = {}
    self.httpd.handlers['get /'] = lambda x: 'abcd'
    self.httpd.cons = {}
    self.httpd.redirect = {}
    self.server_thread = threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval':0.1})
    self.httpd.allow_reuse_address = True
    self.server_thread.daemon = True
    self.httpd.daemon_threads = True

    self.server_thread.start()

  def register(self, key, data):
    self.httpd.handlers[key] = data

  def redirect(self, orig, new):
    self.httpd.redirect[orig] = new

  def notify(self, name, message):
    mbytes = bytes(message, 'utf-8')
    out = struct.pack('BB', 0x81, len(mbytes)) + mbytes
    for con in self.httpd.cons:
      if self.httpd.cons[con].name == name: con.sendall(out)

  def stop(self):
    print('shutdown...')
    self.httpd.shutdown()
    self.httpd.server_close()
    stop = True
    
    self.server_thread.join()


