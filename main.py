import httpd
import readline

s = httpd.httpd()
s.start(8000)
s.redirect('/', '/static/index.html')
s.register('get /a/*', lambda x: 'zzz{0}'.format(x))

while True:
 try:
   m = input()
 except EOFError:
   break
 if len(m) > 0:
   s.notify('/ws/1', m)


s.stop()

