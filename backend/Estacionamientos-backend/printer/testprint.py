from escpos.printer import Network

p = Network("192.168.1.130")

p.text("Hola Vic 👀\n")
p.text("Ya funciona la impresora en red\n\n")
p.cut()