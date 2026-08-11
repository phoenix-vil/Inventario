#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega la pestana Dashboard con metricas de ventas (total, ganancia, top productos).
Uso: cd ~/inventario && python3 agregar_dashboard.py
"""
import os, re, ast, base64

BASE   = os.path.expanduser('~/inventario')
STATIC = os.path.join(BASE, 'static')

DASHBOARD_HTML_B64 = 'PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVzIj4KPGhlYWQ+CjxtZXRhIGNoYXJzZXQ9IlVURi04Ij4KPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiPgo8dGl0bGU+RGFzaGJvYXJkIMK3IE9ubHlSZWVmPC90aXRsZT4KPGxpbmsgcmVsPSJpY29uIiB0eXBlPSJpbWFnZS9wbmciIGhyZWY9Ii9zdGF0aWMvbG9nby5wbmciPgo8c3R5bGU+Cip7Ym94LXNpemluZzpib3JkZXItYm94O21hcmdpbjowO3BhZGRpbmc6MH0KOnJvb3R7CiAgLS1iZzojZjVmNGYwOy0tYmcyOiNmZmY7LS1ib3JkZXI6I2UyZTBkODstLXRleHQ6IzFhMWExODstLXRleHQyOiM2YjZiNjY7CiAgLS1ibHVlOiMxODVmYTU7LS1ibHVlLWJnOiNlNmYxZmI7LS1ncmVlbjojM2I2ZDExOy0tZ3JlZW4tYmc6I2VhZjNkZTsKICAtLWFtYmVyOiM4NTRmMGI7LS1hbWJlci1iZzojZmFlZWRhOy0tcmVkOiNhMzJkMmQ7LS1yZWQtYmc6I2ZjZWJlYgp9CkBtZWRpYShwcmVmZXJzLWNvbG9yLXNjaGVtZTpkYXJrKXs6cm9vdHsKICAtLWJnOiMxYzFjMWE7LS1iZzI6IzI1MjUyMjstLWJvcmRlcjojM2EzYTM2Oy0tdGV4dDojZThlNmRjOy0tdGV4dDI6IzljOWE5MjsKICAtLWJsdWU6Izg1YjdlYjstLWJsdWUtYmc6IzA0MmM1MzstLWdyZWVuOiM5N2M0NTk7LS1ncmVlbi1iZzojMTczNDA0OwogIC0tYW1iZXI6I2VmOWYyNzstLWFtYmVyLWJnOiM0MTI0MDI7LS1yZWQ6I2YwOTU5NTstLXJlZC1iZzojNTAxMzEzCn19CmJvZHl7Zm9udC1mYW1pbHk6LWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1NlZ29lIFVJJyxzYW5zLXNlcmlmO2JhY2tncm91bmQ6dmFyKC0tYmcpO2NvbG9yOnZhcigtLXRleHQpO21pbi1oZWlnaHQ6MTAwdmg7LXdlYmtpdC1mb250LXNtb290aGluZzphbnRpYWxpYXNlZH0KCi8qIFRvcGJhciBob21vbG9nYWRvIGNvbiBlbCByZXN0byBkZSBsYSBhcHAgKi8KLnRvcGJhcntiYWNrZ3JvdW5kOmNvbG9yLW1peChpbiBzcmdiLHZhcigtLWJnMikgODglLHRyYW5zcGFyZW50KTtib3JkZXItYm90dG9tOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7cGFkZGluZzowIDFyZW07aGVpZ2h0OjU0cHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6MTBweDtwb3NpdGlvbjpzdGlja3k7dG9wOjA7ei1pbmRleDoxMDtiYWNrZHJvcC1maWx0ZXI6Ymx1cigxMHB4KX0KLnRvcGJhci10aXRsZXtmb250LXNpemU6MTdweDtmb250LXdlaWdodDo2MDA7ZmxleDoxO3RleHQtYWxpZ246Y2VudGVyO3doaXRlLXNwYWNlOm5vd3JhcDtvdmVyZmxvdzpoaWRkZW47dGV4dC1vdmVyZmxvdzplbGxpcHNpc30KLmJ0bi1pbmljaW97ZGlzcGxheTppbmxpbmUtZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjVweDtoZWlnaHQ6MzZweDtwYWRkaW5nOjAgMTJweDtib3JkZXI6MC41cHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjhweDtiYWNrZ3JvdW5kOnRyYW5zcGFyZW50O2NvbG9yOnZhcigtLXRleHQpO3RleHQtZGVjb3JhdGlvbjpub25lO2ZsZXgtc2hyaW5rOjA7dHJhbnNpdGlvbjpiYWNrZ3JvdW5kIC4xMnN9Ci5idG4taW5pY2lvOmhvdmVye2JhY2tncm91bmQ6dmFyKC0tYmcpfQoudG9wYmFyLXJpZ2h0e2Rpc3BsYXk6ZmxleDtnYXA6NnB4O2FsaWduLWl0ZW1zOmNlbnRlcjtmbGV4LXNocmluazowfQouaWNvbi1idG57aGVpZ2h0OjM2cHg7d2lkdGg6MzZweDtib3JkZXI6MC41cHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjhweDtiYWNrZ3JvdW5kOnRyYW5zcGFyZW50O2ZvbnQtc2l6ZToxNnB4O2N1cnNvcjpwb2ludGVyO2Rpc3BsYXk6aW5saW5lLWZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2p1c3RpZnktY29udGVudDpjZW50ZXI7dHJhbnNpdGlvbjpiYWNrZ3JvdW5kIC4xMnM7Y29sb3I6dmFyKC0tdGV4dCl9Ci5pY29uLWJ0bjpob3ZlcntiYWNrZ3JvdW5kOnZhcigtLWJnKX0KCi5jb250YWluZXJ7bWF4LXdpZHRoOjkwMHB4O21hcmdpbjowIGF1dG87cGFkZGluZzoxLjI1cmVtfQoKLyogUGVzdGHDsWFzIGRlIHBlcsOtb2RvICovCi50YWJzLXBlcmlvZG97ZGlzcGxheTpmbGV4O2dhcDo4cHg7bWFyZ2luLWJvdHRvbToxLjI1cmVtO292ZXJmbG93LXg6YXV0bzstd2Via2l0LW92ZXJmbG93LXNjcm9sbGluZzp0b3VjaH0KLnRhYi1wZXJpb2Rve2ZsZXgtc2hyaW5rOjA7aGVpZ2h0OjM4cHg7cGFkZGluZzowIDE4cHg7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czoxMDBweDtiYWNrZ3JvdW5kOnZhcigtLWJnMik7Y29sb3I6dmFyKC0tdGV4dDIpO2ZvbnQtc2l6ZToxM3B4O2ZvbnQtd2VpZ2h0OjYwMDtjdXJzb3I6cG9pbnRlcjt0cmFuc2l0aW9uOmFsbCAuMTVzfQoudGFiLXBlcmlvZG8uYWN0aXZle2JhY2tncm91bmQ6dmFyKC0tdGV4dCk7Y29sb3I6dmFyKC0tYmcyKTtib3JkZXItY29sb3I6dmFyKC0tdGV4dCl9CgovKiBUYXJqZXRhcyBkZSBlc3RhZMOtc3RpY2FzICovCi5zdGF0cy1ncmlke2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KGF1dG8tZml0LG1pbm1heCgxNTBweCwxZnIpKTtnYXA6MTJweDttYXJnaW4tYm90dG9tOjEuMjVyZW19Ci5zdGF0LWNhcmR7YmFja2dyb3VuZDp2YXIoLS1iZzIpO2JvcmRlcjowLjVweCBzb2xpZCB2YXIoLS1ib3JkZXIpO2JvcmRlci1yYWRpdXM6MTRweDtwYWRkaW5nOjEuMjVyZW07Ym94LXNoYWRvdzowIDFweCAzcHggcmdiYSgwLDAsMCwuMDQpfQouc3RhdC1pY29ue2ZvbnQtc2l6ZToyMnB4O21hcmdpbi1ib3R0b206OHB4fQouc3RhdC1sYWJlbHtmb250LXNpemU6MTJweDtjb2xvcjp2YXIoLS10ZXh0Mik7bWFyZ2luLWJvdHRvbTo0cHh9Ci5zdGF0LXZhbHVle2ZvbnQtc2l6ZToyNHB4O2ZvbnQtd2VpZ2h0OjgwMDtsaW5lLWhlaWdodDoxLjE1fQouc3RhdC12YWx1ZS5ibHVle2NvbG9yOnZhcigtLWJsdWUpfQouc3RhdC12YWx1ZS5ncmVlbntjb2xvcjp2YXIoLS1ncmVlbil9Ci5zdGF0LXZhbHVlLnJlZHtjb2xvcjp2YXIoLS1yZWQpfQouc3RhdC1kZWx0YXtmb250LXNpemU6MTJweDtmb250LXdlaWdodDo2MDA7bWFyZ2luLXRvcDo2cHg7bWluLWhlaWdodDoxNnB4fQouc3RhdC1kZWx0YS51cHtjb2xvcjp2YXIoLS1ncmVlbil9Ci5zdGF0LWRlbHRhLmRvd257Y29sb3I6dmFyKC0tcmVkKX0KCi8qIFRhcmpldGEgZGUgZ3LDoWZpY2EgKi8KLmNoYXJ0LWNhcmR7YmFja2dyb3VuZDp2YXIoLS1iZzIpO2JvcmRlcjowLjVweCBzb2xpZCB2YXIoLS1ib3JkZXIpO2JvcmRlci1yYWRpdXM6MTRweDtwYWRkaW5nOjEuMjVyZW07bWFyZ2luLWJvdHRvbToxLjI1cmVtO2JveC1zaGFkb3c6MCAxcHggM3B4IHJnYmEoMCwwLDAsLjA0KX0KLmNoYXJ0LWhlYWRlcntkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47YWxpZ24taXRlbXM6Y2VudGVyO21hcmdpbi1ib3R0b206MXJlbTtmbGV4LXdyYXA6d3JhcDtnYXA6MTBweH0KLmNoYXJ0LXRpdGxle2ZvbnQtc2l6ZToxNXB4O2ZvbnQtd2VpZ2h0OjYwMH0KLmNoYXJ0LWxlZ2VuZHtkaXNwbGF5OmZsZXg7Z2FwOjE0cHg7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tdGV4dDIpfQoubGVnZW5kLWRvdHtkaXNwbGF5OmlubGluZS1ibG9jazt3aWR0aDo5cHg7aGVpZ2h0OjlweDtib3JkZXItcmFkaXVzOjUwJTttYXJnaW4tcmlnaHQ6NHB4O3ZlcnRpY2FsLWFsaWduOm1pZGRsZX0KLmNoYXJ0LXRvZ2dsZXtkaXNwbGF5OmZsZXg7Z2FwOjRweH0KLmNoYXJ0LXRvZ2dsZSBidXR0b257aGVpZ2h0OjMwcHg7cGFkZGluZzowIDEycHg7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czo4cHg7YmFja2dyb3VuZDp0cmFuc3BhcmVudDtjb2xvcjp2YXIoLS10ZXh0Mik7Zm9udC1zaXplOjEycHg7Y3Vyc29yOnBvaW50ZXI7dHJhbnNpdGlvbjphbGwgLjEyc30KLmNoYXJ0LXRvZ2dsZSBidXR0b24uYWN0aXZle2JhY2tncm91bmQ6dmFyKC0tdGV4dCk7Y29sb3I6dmFyKC0tYmcyKTtib3JkZXItY29sb3I6dmFyKC0tdGV4dCl9Ci5jaGFydC1hcmVhe2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpmbGV4LWVuZDtnYXA6NnB4O2hlaWdodDoxNzBweDtvdmVyZmxvdy14OmF1dG87cGFkZGluZy1ib3R0b206NHB4Oy13ZWJraXQtb3ZlcmZsb3ctc2Nyb2xsaW5nOnRvdWNofQouY2hhcnQtY29se2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47YWxpZ24taXRlbXM6Y2VudGVyO2ZsZXg6MTttaW4td2lkdGg6MjJweH0KLmNoYXJ0LWJhcnMtd3JhcHtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6ZmxleC1lbmQ7Z2FwOjJweDtoZWlnaHQ6MTMwcHg7d2lkdGg6MTAwJX0KLmNoYXJ0LWJhcntmbGV4OjE7Ym9yZGVyLXJhZGl1czo0cHggNHB4IDAgMDttaW4taGVpZ2h0OjJweDt0cmFuc2l0aW9uOmhlaWdodCAuNHMgZWFzZX0KLmNoYXJ0LWJhci12ZW50YXtiYWNrZ3JvdW5kOnZhcigtLWJsdWUpfQouY2hhcnQtYmFyLWdhbmFuY2lhe2JhY2tncm91bmQ6dmFyKC0tZ3JlZW4pfQouY2hhcnQtbGFiZWx7Zm9udC1zaXplOjlweDtjb2xvcjp2YXIoLS10ZXh0Mik7bWFyZ2luLXRvcDo2cHg7d2hpdGUtc3BhY2U6bm93cmFwfQoKLyogVG9wIHByb2R1Y3RvcyAqLwouc2VjdGlvbi10aXRsZXtmb250LXNpemU6MTVweDtmb250LXdlaWdodDo2MDA7bWFyZ2luLWJvdHRvbTouNzVyZW07ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6NnB4fQouY2FyZHtiYWNrZ3JvdW5kOnZhcigtLWJnMik7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czoxNHB4O3BhZGRpbmc6LjVyZW0gMS4yNXJlbTtib3gtc2hhZG93OjAgMXB4IDNweCByZ2JhKDAsMCwwLC4wNCk7bWFyZ2luLWJvdHRvbToxLjVyZW19Ci50cC1yb3d7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6MTJweDtwYWRkaW5nOi43NXJlbSAwO2JvcmRlci1ib3R0b206MC41cHggc29saWQgdmFyKC0tYm9yZGVyKX0KLnRwLXJvdzpsYXN0LWNoaWxke2JvcmRlci1ib3R0b206bm9uZX0KLnRwLWZpcnN0e2JhY2tncm91bmQ6bGluZWFyLWdyYWRpZW50KDkwZGVnLGNvbG9yLW1peChpbiBzcmdiLHZhcigtLWFtYmVyLWJnKSA3MCUsdHJhbnNwYXJlbnQpLHRyYW5zcGFyZW50KTtib3JkZXItcmFkaXVzOjEwcHg7cGFkZGluZzouNzVyZW0gLjVyZW07bWFyZ2luOjAgLTAuNXJlbX0KLnRwLXJhbmt7Zm9udC1zaXplOjIwcHg7d2lkdGg6MzBweDt0ZXh0LWFsaWduOmNlbnRlcjtmbGV4LXNocmluazowfQoudHAtaW1nLC50cC1pbWctcGh7d2lkdGg6NDRweDtoZWlnaHQ6NDRweDtib3JkZXItcmFkaXVzOjhweDtvYmplY3QtZml0OmNvdmVyO2ZsZXgtc2hyaW5rOjA7YmFja2dyb3VuZDp2YXIoLS1iZyk7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6Y2VudGVyO2ZvbnQtc2l6ZToyMHB4fQoudHAtaW5mb3tmbGV4OjE7bWluLXdpZHRoOjB9Ci50cC1uYW1le2ZvbnQtd2VpZ2h0OjYwMDtmb250LXNpemU6MTRweDt3aGl0ZS1zcGFjZTpub3dyYXA7b3ZlcmZsb3c6aGlkZGVuO3RleHQtb3ZlcmZsb3c6ZWxsaXBzaXN9Ci50cC1tZXRhe2ZvbnQtc2l6ZToxMnB4O2NvbG9yOnZhcigtLXRleHQyKTttYXJnaW4tdG9wOjFweH0KLnRwLWJhci10cmFja3toZWlnaHQ6NXB4O2JhY2tncm91bmQ6dmFyKC0tYmcpO2JvcmRlci1yYWRpdXM6MTBweDttYXJnaW4tdG9wOjZweDtvdmVyZmxvdzpoaWRkZW59Ci50cC1iYXItZmlsbHtoZWlnaHQ6MTAwJTtiYWNrZ3JvdW5kOnZhcigtLWJsdWUpO2JvcmRlci1yYWRpdXM6MTBweDt0cmFuc2l0aW9uOndpZHRoIC41cyBlYXNlfQoudHAtbnVtc3t0ZXh0LWFsaWduOnJpZ2h0O2ZsZXgtc2hyaW5rOjB9Ci50cC10b3RhbHtmb250LXdlaWdodDo3MDA7Zm9udC1zaXplOjE0cHh9Ci50cC1nYW5hbmNpYXtmb250LXNpemU6MTFweDtjb2xvcjp2YXIoLS1ncmVlbik7Zm9udC13ZWlnaHQ6NjAwfQoKLmVtcHR5e3RleHQtYWxpZ246Y2VudGVyO3BhZGRpbmc6Mi41cmVtIDFyZW07Y29sb3I6dmFyKC0tdGV4dDIpO2ZvbnQtc2l6ZToxNHB4fQpAbWVkaWEobWF4LXdpZHRoOjYwMHB4KXsudG9wYmFye3BhZGRpbmc6MCAuNjI1cmVtfS50b3BiYXItdGl0bGV7Zm9udC1zaXplOjE1cHh9LnN0YXQtdmFsdWV7Zm9udC1zaXplOjIwcHh9fQo8L3N0eWxlPgo8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Ii9zdGF0aWMvbW9kZXJuLmNzcyI+CjwvaGVhZD4KPGJvZHk+Cgo8ZGl2IGNsYXNzPSJ0b3BiYXIiPgogIDxhIGhyZWY9Ii8iIGNsYXNzPSJidG4taW5pY2lvIiB0aXRsZT0iSW5pY2lvIj48aW1nIHNyYz0iL3N0YXRpYy9sb2dvLnBuZyIgYWx0PSJPbmx5UmVlZiIgc3R5bGU9ImhlaWdodDozNnB4O3dpZHRoOmF1dG87ZGlzcGxheTpibG9jayI+PC9hPgogIDxoMSBjbGFzcz0idG9wYmFyLXRpdGxlIj7wn5OKIERhc2hib2FyZDwvaDE+CiAgPGRpdiBjbGFzcz0idG9wYmFyLXJpZ2h0Ij4KICAgIDxidXR0b24gY2xhc3M9Imljb24tYnRuIiBvbmNsaWNrPSJjYXJnYXJUb2RvKCk7Y2FyZ2FyU2VyaWUoKTsiIHRpdGxlPSJBY3R1YWxpemFyIj7ihrs8L2J1dHRvbj4KICA8L2Rpdj4KPC9kaXY+Cgo8ZGl2IGNsYXNzPSJjb250YWluZXIiPgoKICA8ZGl2IGNsYXNzPSJ0YWJzLXBlcmlvZG8iIGlkPSJ0YWJzLXBlcmlvZG8iPgogICAgPGJ1dHRvbiBjbGFzcz0idGFiLXBlcmlvZG8gYWN0aXZlIiBkYXRhLXBlcmlvZG89ImhveSIgb25jbGljaz0iY2FtYmlhclBlcmlvZG8oJ2hveScpIj5Ib3k8L2J1dHRvbj4KICAgIDxidXR0b24gY2xhc3M9InRhYi1wZXJpb2RvIiBkYXRhLXBlcmlvZG89InNlbWFuYSIgb25jbGljaz0iY2FtYmlhclBlcmlvZG8oJ3NlbWFuYScpIj5TZW1hbmE8L2J1dHRvbj4KICAgIDxidXR0b24gY2xhc3M9InRhYi1wZXJpb2RvIiBkYXRhLXBlcmlvZG89Im1lcyIgb25jbGljaz0iY2FtYmlhclBlcmlvZG8oJ21lcycpIj5NZXM8L2J1dHRvbj4KICAgIDxidXR0b24gY2xhc3M9InRhYi1wZXJpb2RvIiBkYXRhLXBlcmlvZG89InRvZG8iIG9uY2xpY2s9ImNhbWJpYXJQZXJpb2RvKCd0b2RvJykiPlRvZG88L2J1dHRvbj4KICA8L2Rpdj4KCiAgPGRpdiBjbGFzcz0ic3RhdHMtZ3JpZCI+CiAgICA8ZGl2IGNsYXNzPSJzdGF0LWNhcmQiPgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LWljb24iPvCfkrA8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ic3RhdC1sYWJlbCI+VG90YWwgdmVuZGlkbzwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LXZhbHVlIGJsdWUiIGlkPSJzdC10b3RhbCI+4oCUPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9InN0YXQtZGVsdGEiIGlkPSJzdC10b3RhbC1kZWx0YSI+PC9kaXY+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9InN0YXQtY2FyZCI+CiAgICAgIDxkaXYgY2xhc3M9InN0YXQtaWNvbiI+8J+TiDwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LWxhYmVsIj5HYW5hbmNpYTxzcGFuIGlkPSJzdC1tYXJnZW4tYmFkZ2UiPjwvc3Bhbj48L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ic3RhdC12YWx1ZSBncmVlbiIgaWQ9InN0LWdhbmFuY2lhIj7igJQ8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ic3RhdC1kZWx0YSIgaWQ9InN0LWdhbmFuY2lhLWRlbHRhIj48L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0ic3RhdC1jYXJkIj4KICAgICAgPGRpdiBjbGFzcz0ic3RhdC1pY29uIj7wn6e+PC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9InN0YXQtbGFiZWwiPlZlbnRhczwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LXZhbHVlIiBpZD0ic3QtbnVtLXZlbnRhcyI+4oCUPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9InN0YXQtZGVsdGEiPiZuYnNwOzwvZGl2PgogICAgPC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJzdGF0LWNhcmQiPgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LWljb24iPvCfjqs8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ic3RhdC1sYWJlbCI+VGlja2V0IHByb21lZGlvPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9InN0YXQtdmFsdWUiIGlkPSJzdC10aWNrZXQiPuKAlDwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJzdGF0LWRlbHRhIj4mbmJzcDs8L2Rpdj4KICAgIDwvZGl2PgogIDwvZGl2PgoKICA8ZGl2IGNsYXNzPSJjaGFydC1jYXJkIj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LWhlYWRlciI+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXRpdGxlIj5UZW5kZW5jaWEgZGUgdmVudGFzPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LWxlZ2VuZCI+CiAgICAgICAgPHNwYW4+PHNwYW4gY2xhc3M9ImxlZ2VuZC1kb3QiIHN0eWxlPSJiYWNrZ3JvdW5kOnZhcigtLWJsdWUpIj48L3NwYW4+VmVuZGlkbzwvc3Bhbj4KICAgICAgICA8c3Bhbj48c3BhbiBjbGFzcz0ibGVnZW5kLWRvdCIgc3R5bGU9ImJhY2tncm91bmQ6dmFyKC0tZ3JlZW4pIj48L3NwYW4+R2FuYW5jaWE8L3NwYW4+CiAgICAgIDwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10b2dnbGUiPgogICAgICAgIDxidXR0b24gZGF0YS1kaWFzPSI3IiBvbmNsaWNrPSJjYW1iaWFyRGlhc0NoYXJ0KDcpIj43IGTDrWFzPC9idXR0b24+CiAgICAgICAgPGJ1dHRvbiBkYXRhLWRpYXM9IjE0IiBjbGFzcz0iYWN0aXZlIiBvbmNsaWNrPSJjYW1iaWFyRGlhc0NoYXJ0KDE0KSI+MTQgZMOtYXM8L2J1dHRvbj4KICAgICAgICA8YnV0dG9uIGRhdGEtZGlhcz0iMzAiIG9uY2xpY2s9ImNhbWJpYXJEaWFzQ2hhcnQoMzApIj4zMCBkw61hczwvYnV0dG9uPgogICAgICA8L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iY2hhcnQtYXJlYSIgaWQ9ImNoYXJ0LWJhcnMiPgogICAgICA8ZGl2IGNsYXNzPSJlbXB0eSI+Q2FyZ2FuZG8uLi48L2Rpdj4KICAgIDwvZGl2PgogIDwvZGl2PgoKICA8ZGl2IGNsYXNzPSJzZWN0aW9uLXRpdGxlIj7wn4+GIFByb2R1Y3RvcyBtw6FzIHZlbmRpZG9zPC9kaXY+CiAgPGRpdiBjbGFzcz0iY2FyZCIgaWQ9InRvcC1wcm9kdWN0b3MiPgogICAgPGRpdiBjbGFzcz0iZW1wdHkiPkNhcmdhbmRvLi4uPC9kaXY+CiAgPC9kaXY+Cgo8L2Rpdj4KCjxzY3JpcHQgc3JjPSIvc3RhdGljL2F1dGguanMiPjwvc2NyaXB0Pgo8c2NyaXB0PgpyZXF1aXJlR2VyZW50ZSgpOwoKbGV0IHBlcmlvZG9BY3R1YWwgPSAnaG95JzsKbGV0IGRpYXNDaGFydCA9IDE0OwoKZnVuY3Rpb24gZXNjKHMpe3JldHVybiBTdHJpbmcocykucmVwbGFjZSgvJi9nLCcmYW1wOycpLnJlcGxhY2UoLzwvZywnJmx0OycpLnJlcGxhY2UoLz4vZywnJmd0OycpO30KZnVuY3Rpb24gbW9uZXkobil7cmV0dXJuICckJytOdW1iZXIobnx8MCkudG9Mb2NhbGVTdHJpbmcoJ2VzLU1YJyx7bWluaW11bUZyYWN0aW9uRGlnaXRzOjIsbWF4aW11bUZyYWN0aW9uRGlnaXRzOjJ9KTt9CgpmdW5jdGlvbiBsaW1pdGVzUGVyaW9kbyhwZXJpb2RvKXsKICBjb25zdCBhaG9yYSA9IG5ldyBEYXRlKCk7CiAgbGV0IGRlc2RlID0gbnVsbDsKICBpZihwZXJpb2RvID09PSAnaG95Jyl7CiAgICBkZXNkZSA9IG5ldyBEYXRlKGFob3JhLmdldEZ1bGxZZWFyKCksIGFob3JhLmdldE1vbnRoKCksIGFob3JhLmdldERhdGUoKSwgMCwwLDApOwogIH0gZWxzZSBpZihwZXJpb2RvID09PSAnc2VtYW5hJyl7CiAgICBjb25zdCBkaWFTZW1hbmEgPSAoYWhvcmEuZ2V0RGF5KCkrNiklNzsgLy8gMCA9IGx1bmVzCiAgICBkZXNkZSA9IG5ldyBEYXRlKGFob3JhLmdldEZ1bGxZZWFyKCksIGFob3JhLmdldE1vbnRoKCksIGFob3JhLmdldERhdGUoKS1kaWFTZW1hbmEsIDAsMCwwKTsKICB9IGVsc2UgaWYocGVyaW9kbyA9PT0gJ21lcycpewogICAgZGVzZGUgPSBuZXcgRGF0ZShhaG9yYS5nZXRGdWxsWWVhcigpLCBhaG9yYS5nZXRNb250aCgpLCAxLCAwLDAsMCk7CiAgfQogIHJldHVybiBkZXNkZSA/IGRlc2RlLnRvSVNPU3RyaW5nKCkgOiBudWxsOwp9CgpmdW5jdGlvbiBsYWJlbFBlcmlvZG9BbnRlcmlvcigpewogIGlmKHBlcmlvZG9BY3R1YWw9PT0naG95JykgcmV0dXJuICdheWVyJzsKICBpZihwZXJpb2RvQWN0dWFsPT09J3NlbWFuYScpIHJldHVybiAnc2VtYW5hIHBhc2FkYSc7CiAgaWYocGVyaW9kb0FjdHVhbD09PSdtZXMnKSByZXR1cm4gJ21lcyBwYXNhZG8nOwogIHJldHVybiAnJzsKfQoKZnVuY3Rpb24gY2FtYmlhclBlcmlvZG8ocCl7CiAgcGVyaW9kb0FjdHVhbCA9IHA7CiAgZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRhYi1wZXJpb2RvJykuZm9yRWFjaChiPT5iLmNsYXNzTGlzdC50b2dnbGUoJ2FjdGl2ZScsIGIuZGF0YXNldC5wZXJpb2RvPT09cCkpOwogIGNhcmdhclRvZG8oKTsKfQoKZnVuY3Rpb24gY2FtYmlhckRpYXNDaGFydChkKXsKICBkaWFzQ2hhcnQgPSBkOwogIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy5jaGFydC10b2dnbGUgYnV0dG9uJykuZm9yRWFjaChiPT5iLmNsYXNzTGlzdC50b2dnbGUoJ2FjdGl2ZScsIHBhcnNlSW50KGIuZGF0YXNldC5kaWFzKT09PWQpKTsKICBjYXJnYXJTZXJpZSgpOwp9Cgphc3luYyBmdW5jdGlvbiBjYXJnYXJUb2RvKCl7CiAgYXdhaXQgUHJvbWlzZS5hbGwoW2NhcmdhclJlc3VtZW4oKSwgY2FyZ2FyVG9wUHJvZHVjdG9zKCldKTsKfQoKZnVuY3Rpb24gcmVuZGVyRGVsdGEoZWxJZCwgcGN0KXsKICBjb25zdCBlbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKGVsSWQpOwogIGlmKHBjdCA9PT0gbnVsbCB8fCBwY3QgPT09IHVuZGVmaW5lZCl7IGVsLnRleHRDb250ZW50PScnOyByZXR1cm47IH0KICBjb25zdCBzdWJpbyA9IHBjdCA+PSAwOwogIGVsLmNsYXNzTmFtZSA9ICdzdGF0LWRlbHRhICcgKyAoc3ViaW8gPyAndXAnIDogJ2Rvd24nKTsKICBlbC50ZXh0Q29udGVudCA9IChzdWJpbz8n4payICc6J+KWvCAnKSArIE1hdGguYWJzKHBjdCkgKyAnJSB2cyAnICsgbGFiZWxQZXJpb2RvQW50ZXJpb3IoKTsKfQoKYXN5bmMgZnVuY3Rpb24gY2FyZ2FyUmVzdW1lbigpewogIGNvbnN0IGRlc2RlID0gbGltaXRlc1BlcmlvZG8ocGVyaW9kb0FjdHVhbCk7CiAgY29uc3QgcGFyYW1zID0gbmV3IFVSTFNlYXJjaFBhcmFtcygpOwogIGlmKGRlc2RlKSBwYXJhbXMuc2V0KCdkZXNkZScsIGRlc2RlKTsKICBwYXJhbXMuc2V0KCdwZXJpb2RvJywgcGVyaW9kb0FjdHVhbCk7CiAgdHJ5ewogICAgY29uc3QgciA9IGF3YWl0IGF1dGhGZXRjaCgnL2FwaS9kYXNoYm9hcmQvcmVzdW1lbj8nK3BhcmFtcy50b1N0cmluZygpKTsKICAgIGNvbnN0IGQgPSBhd2FpdCByLmpzb24oKTsKCiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3QtdG90YWwnKS50ZXh0Q29udGVudCA9IG1vbmV5KGQudG90YWxfdmVuZGlkbyk7CiAgICBjb25zdCBnRWwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3QtZ2FuYW5jaWEnKTsKICAgIGdFbC50ZXh0Q29udGVudCA9IG1vbmV5KGQuZ2FuYW5jaWEpOwogICAgZ0VsLmNsYXNzTmFtZSA9ICdzdGF0LXZhbHVlICcgKyAoZC5nYW5hbmNpYSA+PSAwID8gJ2dyZWVuJyA6ICdyZWQnKTsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzdC1tYXJnZW4tYmFkZ2UnKS50ZXh0Q29udGVudCA9IGQudG90YWxfdmVuZGlkbz4wID8gJyDCtyAnICsgZC5tYXJnZW5fcGN0ICsgJyUnIDogJyc7CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3QtbnVtLXZlbnRhcycpLnRleHRDb250ZW50ID0gZC5udW1fdmVudGFzOwogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0LXRpY2tldCcpLnRleHRDb250ZW50ID0gbW9uZXkoZC50aWNrZXRfcHJvbWVkaW8pOwoKICAgIGlmKGQuY29tcGFyYXRpdm8pewogICAgICByZW5kZXJEZWx0YSgnc3QtdG90YWwtZGVsdGEnLCBkLmNvbXBhcmF0aXZvLnZhcmlhY2lvbl90b3RhbF9wY3QpOwogICAgICByZW5kZXJEZWx0YSgnc3QtZ2FuYW5jaWEtZGVsdGEnLCBkLmNvbXBhcmF0aXZvLnZhcmlhY2lvbl9nYW5hbmNpYV9wY3QpOwogICAgfSBlbHNlIHsKICAgICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0LXRvdGFsLWRlbHRhJykudGV4dENvbnRlbnQgPSAnJzsKICAgICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0LWdhbmFuY2lhLWRlbHRhJykudGV4dENvbnRlbnQgPSAnJzsKICAgIH0KICB9Y2F0Y2goZSl7IGNvbnNvbGUuZXJyb3IoZSk7IH0KfQoKYXN5bmMgZnVuY3Rpb24gY2FyZ2FyU2VyaWUoKXsKICBjb25zdCBjb250ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2NoYXJ0LWJhcnMnKTsKICB0cnl7CiAgICBjb25zdCByID0gYXdhaXQgYXV0aEZldGNoKCcvYXBpL2Rhc2hib2FyZC9zZXJpZS1kaWFyaWE/ZGlhcz0nK2RpYXNDaGFydCk7CiAgICBjb25zdCBzZXJpZSA9IGF3YWl0IHIuanNvbigpOwogICAgcmVuZGVyQ2hhcnQoc2VyaWUpOwogIH1jYXRjaChlKXsKICAgIGNvbnQuaW5uZXJIVE1MID0gJzxkaXYgY2xhc3M9ImVtcHR5Ij5FcnJvciBhbCBjYXJnYXIgbGEgZ3LDoWZpY2E8L2Rpdj4nOwogIH0KfQoKZnVuY3Rpb24gcmVuZGVyQ2hhcnQoc2VyaWUpewogIGNvbnN0IGNvbnQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnY2hhcnQtYmFycycpOwogIGlmKCFzZXJpZS5sZW5ndGgpeyBjb250LmlubmVySFRNTCA9ICc8ZGl2IGNsYXNzPSJlbXB0eSI+U2luIGRhdG9zPC9kaXY+JzsgcmV0dXJuOyB9CiAgY29uc3QgbWF4VmFsID0gTWF0aC5tYXgoMSwgLi4uc2VyaWUubWFwKGQ9Pk1hdGgubWF4KGQudG90YWwsIGQuZ2FuYW5jaWEpKSk7CiAgY29udC5pbm5lckhUTUwgPSBzZXJpZS5tYXAoZD0+ewogICAgY29uc3QgYWx0dXJhVmVudGEgPSBNYXRoLm1heCgyLCBNYXRoLnJvdW5kKChkLnRvdGFsL21heFZhbCkqMTAwKSk7CiAgICBjb25zdCBhbHR1cmFHYW4gPSBNYXRoLm1heCgwLCBNYXRoLnJvdW5kKChNYXRoLm1heCgwLGQuZ2FuYW5jaWEpL21heFZhbCkqMTAwKSk7CiAgICBjb25zdCBmZWNoYU9iaiA9IG5ldyBEYXRlKGQuZmVjaGErJ1QwMDowMDowMCcpOwogICAgY29uc3QgZGlhTGFiZWwgPSBmZWNoYU9iai50b0xvY2FsZURhdGVTdHJpbmcoJ2VzLU1YJyx7ZGF5OidudW1lcmljJywgbW9udGg6J3Nob3J0J30pOwogICAgY29uc3QgdG9vbHRpcCA9IGAke2RpYUxhYmVsfTogJHttb25leShkLnRvdGFsKX0gdmVuZGlkbywgJHttb25leShkLmdhbmFuY2lhKX0gZ2FuYW5jaWEgKCR7ZC5udW1fdmVudGFzfSB2ZW50YXMpYDsKICAgIHJldHVybiBgPGRpdiBjbGFzcz0iY2hhcnQtY29sIiB0aXRsZT0iJHtlc2ModG9vbHRpcCl9Ij4KICAgICAgPGRpdiBjbGFzcz0iY2hhcnQtYmFycy13cmFwIj4KICAgICAgICA8ZGl2IGNsYXNzPSJjaGFydC1iYXIgY2hhcnQtYmFyLXZlbnRhIiBzdHlsZT0iaGVpZ2h0OiR7YWx0dXJhVmVudGF9JSI+PC9kaXY+CiAgICAgICAgPGRpdiBjbGFzcz0iY2hhcnQtYmFyIGNoYXJ0LWJhci1nYW5hbmNpYSIgc3R5bGU9ImhlaWdodDoke2FsdHVyYUdhbn0lIj48L2Rpdj4KICAgICAgPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LWxhYmVsIj4ke2RpYUxhYmVsfTwvZGl2PgogICAgPC9kaXY+YDsKICB9KS5qb2luKCcnKTsKfQoKYXN5bmMgZnVuY3Rpb24gY2FyZ2FyVG9wUHJvZHVjdG9zKCl7CiAgY29uc3QgZGVzZGUgPSBsaW1pdGVzUGVyaW9kbyhwZXJpb2RvQWN0dWFsKTsKICBjb25zdCBwYXJhbXMgPSBuZXcgVVJMU2VhcmNoUGFyYW1zKCk7CiAgaWYoZGVzZGUpIHBhcmFtcy5zZXQoJ2Rlc2RlJywgZGVzZGUpOwogIHBhcmFtcy5zZXQoJ2xpbWl0JywgJzUnKTsKICBjb25zdCBjb250ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3RvcC1wcm9kdWN0b3MnKTsKICB0cnl7CiAgICBjb25zdCByID0gYXdhaXQgYXV0aEZldGNoKCcvYXBpL2Rhc2hib2FyZC90b3AtcHJvZHVjdG9zPycrcGFyYW1zLnRvU3RyaW5nKCkpOwogICAgY29uc3QgcHJvZHVjdG9zID0gYXdhaXQgci5qc29uKCk7CiAgICByZW5kZXJUb3BQcm9kdWN0b3MocHJvZHVjdG9zKTsKICB9Y2F0Y2goZSl7CiAgICBjb250LmlubmVySFRNTCA9ICc8ZGl2IGNsYXNzPSJlbXB0eSI+RXJyb3IgYWwgY2FyZ2FyPC9kaXY+JzsKICB9Cn0KCmZ1bmN0aW9uIHJlbmRlclRvcFByb2R1Y3Rvcyhwcm9kdWN0b3MpewogIGNvbnN0IGNvbnQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgndG9wLXByb2R1Y3RvcycpOwogIGlmKCFwcm9kdWN0b3MubGVuZ3RoKXsKICAgIGNvbnQuaW5uZXJIVE1MID0gJzxkaXYgY2xhc3M9ImVtcHR5Ij5TaW4gdmVudGFzIGVuIGVzdGUgcGVyw61vZG88L2Rpdj4nOwogICAgcmV0dXJuOwogIH0KICBjb25zdCBtYXhDYW50ID0gTWF0aC5tYXgoLi4ucHJvZHVjdG9zLm1hcChwPT5wLmNhbnRpZGFkX3ZlbmRpZGEpLCAxKTsKICBjb25zdCBtZWRhbGxhcyA9IFsn8J+lhycsJ/CfpYgnLCfwn6WJJ107CiAgY29udC5pbm5lckhUTUwgPSBwcm9kdWN0b3MubWFwKChwLGkpPT57CiAgICBjb25zdCBwY3QgPSBNYXRoLnJvdW5kKChwLmNhbnRpZGFkX3ZlbmRpZGEvbWF4Q2FudCkqMTAwKTsKICAgIGNvbnN0IG1lZGFsbGEgPSBtZWRhbGxhc1tpXSB8fCAoJyMnKyhpKzEpKTsKICAgIGNvbnN0IGltZyA9IHAuaW1hZ2VuX3VybAogICAgICA/IGA8aW1nIHNyYz0iJHtlc2MocC5pbWFnZW5fdXJsKX0iIGNsYXNzPSJ0cC1pbWciIGFsdD0iIiBvbmVycm9yPSJ0aGlzLm91dGVySFRNTD0nPGRpdiBjbGFzcz10cC1pbWctcGg+8J+TpjwvZGl2PiciPmAKICAgICAgOiBgPGRpdiBjbGFzcz0idHAtaW1nLXBoIj7wn5OmPC9kaXY+YDsKICAgIHJldHVybiBgPGRpdiBjbGFzcz0idHAtcm93ICR7aT09PTA/J3RwLWZpcnN0JzonJ30iPgogICAgICA8ZGl2IGNsYXNzPSJ0cC1yYW5rIj4ke21lZGFsbGF9PC9kaXY+CiAgICAgICR7aW1nfQogICAgICA8ZGl2IGNsYXNzPSJ0cC1pbmZvIj4KICAgICAgICA8ZGl2IGNsYXNzPSJ0cC1uYW1lIj4ke2VzYyhwLm5vbWJyZSl9PC9kaXY+CiAgICAgICAgPGRpdiBjbGFzcz0idHAtbWV0YSI+JHtwLm1hcmNhP2VzYyhwLm1hcmNhKSsnIMK3ICc6Jyd9JHtwLmNhbnRpZGFkX3ZlbmRpZGF9IHZlbmRpZG9zPC9kaXY+CiAgICAgICAgPGRpdiBjbGFzcz0idHAtYmFyLXRyYWNrIj48ZGl2IGNsYXNzPSJ0cC1iYXItZmlsbCIgc3R5bGU9IndpZHRoOiR7cGN0fSUiPjwvZGl2PjwvZGl2PgogICAgICA8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0idHAtbnVtcyI+CiAgICAgICAgPGRpdiBjbGFzcz0idHAtdG90YWwiPiR7bW9uZXkocC50b3RhbF92ZW5kaWRvKX08L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJ0cC1nYW5hbmNpYSI+KyR7bW9uZXkocC5nYW5hbmNpYSl9PC9kaXY+CiAgICAgIDwvZGl2PgogICAgPC9kaXY+YDsKICB9KS5qb2luKCcnKTsKfQoKY2FyZ2FyVG9kbygpOwpjYXJnYXJTZXJpZSgpOwo8L3NjcmlwdD4KPC9ib2R5Pgo8L2h0bWw+Cg=='

# ================================================================
# 1. Crear static/dashboard.html (archivo nuevo, sin riesgo de romper otros)
# ================================================================
print("1. Creando static/dashboard.html...")
dashboard_path = os.path.join(STATIC, 'dashboard.html')
with open(dashboard_path, 'wb') as f:
    f.write(base64.b64decode(DASHBOARD_HTML_B64))
print("   OK dashboard.html creado (" + str(os.path.getsize(dashboard_path)) + " bytes)")

# ================================================================
# 2. Backend: agregar timedelta al import de datetime si falta
# ================================================================
print("2. Verificando imports en main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()
original_src = src

m = re.search(r'from datetime import ([^\n]+)', src)
if m and 'timedelta' not in m.group(1):
    nueva_linea = 'from datetime import ' + m.group(1).strip() + ', timedelta'
    src = src.replace(m.group(0), nueva_linea, 1)
    print("   OK timedelta agregado al import de datetime")
elif m:
    print("   * timedelta ya estaba importado")
else:
    print("   ADVERTENCIA: no se encontro 'from datetime import ...' en main.py")

# ================================================================
# 3. Backend: agregar endpoints del dashboard (si no existen ya)
# ================================================================
if '/api/dashboard/resumen' in src:
    print("3. Los endpoints del dashboard ya existian, se omite este paso")
else:
    print("3. Agregando endpoints del dashboard...")
    endpoints = '''

# ─── Dashboard: metricas de ventas ──────────────────────────────────────────

def _rango_utc_dash(desde):
    """Convierte una fecha ISO (con offset de horario local) a datetime UTC naive."""
    if not desde:
        return None
    try:
        d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d
    except ValueError:
        return None


def _costo_por_producto_dash(db, ids):
    if not ids:
        return {}
    rows = db.query(Producto.id, Producto.precio_costo).filter(Producto.id.in_(ids)).all()
    return {pid: (costo or 0) for pid, costo in rows}


def _calcular_periodo_dash(db, desde_dt, hasta_dt):
    q = db.query(Venta)
    if desde_dt:
        q = q.filter(Venta.creado_en >= desde_dt)
    if hasta_dt:
        q = q.filter(Venta.creado_en < hasta_dt)
    ventas = q.all()

    ids = set()
    detalles = []
    for v in ventas:
        det = json.loads(v.detalle_json)
        detalles.append(det)
        for it in det:
            ids.add(it.get("producto_id"))
    costos = _costo_por_producto_dash(db, ids)

    total_vendido = round(sum(v.total for v in ventas), 2)
    total_costo = 0.0
    for det in detalles:
        for it in det:
            total_costo += costos.get(it.get("producto_id"), 0) * it.get("cantidad", 0)
    total_costo = round(total_costo, 2)
    ganancia = round(total_vendido - total_costo, 2)
    num_ventas = len(ventas)

    return {
        "num_ventas": num_ventas,
        "total_vendido": total_vendido,
        "total_costo": total_costo,
        "ganancia": ganancia,
        "margen_pct": round(ganancia / total_vendido * 100, 1) if total_vendido > 0 else 0,
        "ticket_promedio": round(total_vendido / num_ventas, 2) if num_ventas else 0,
    }


@app.get("/api/dashboard/resumen")
def dashboard_resumen(
    desde: Optional[str] = Query(None),
    periodo: str = Query("todo"),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d = _rango_utc_dash(desde)
    actual = _calcular_periodo_dash(db, d, None)

    comparativo = None
    if d and periodo in ("hoy", "semana", "mes"):
        if periodo == "hoy":
            anterior_desde = d - timedelta(days=1)
            anterior_hasta = d
        elif periodo == "semana":
            anterior_desde = d - timedelta(days=7)
            anterior_hasta = d
        else:  # mes
            if d.month == 1:
                anterior_desde = d.replace(year=d.year - 1, month=12, day=1)
            else:
                anterior_desde = d.replace(month=d.month - 1, day=1)
            anterior_hasta = d

        previo = _calcular_periodo_dash(db, anterior_desde, anterior_hasta)

        def variacion(actual_v, prev_v):
            if prev_v <= 0:
                return None
            return round((actual_v - prev_v) / prev_v * 100, 1)

        comparativo = {
            "total_vendido": previo["total_vendido"],
            "ganancia": previo["ganancia"],
            "variacion_total_pct": variacion(actual["total_vendido"], previo["total_vendido"]),
            "variacion_ganancia_pct": variacion(actual["ganancia"], previo["ganancia"]),
        }

    actual["comparativo"] = comparativo
    return actual


@app.get("/api/dashboard/serie-diaria")
def dashboard_serie_diaria(
    dias: int = Query(14, ge=1, le=90),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    ahora = datetime.utcnow()
    desde = (ahora - timedelta(days=dias - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    ventas = db.query(Venta).filter(Venta.creado_en >= desde).all()

    ids = set()
    for v in ventas:
        for it in json.loads(v.detalle_json):
            ids.add(it.get("producto_id"))
    costos = _costo_por_producto_dash(db, ids)

    dias_map = {}
    for i in range(dias):
        fecha = (desde + timedelta(days=i)).strftime("%Y-%m-%d")
        dias_map[fecha] = {"total": 0.0, "ganancia": 0.0, "num_ventas": 0}

    for v in ventas:
        fecha = v.creado_en.strftime("%Y-%m-%d")
        if fecha not in dias_map:
            continue
        costo_venta = sum(
            costos.get(it.get("producto_id"), 0) * it.get("cantidad", 0)
            for it in json.loads(v.detalle_json)
        )
        dias_map[fecha]["total"] += v.total
        dias_map[fecha]["ganancia"] += (v.total - costo_venta)
        dias_map[fecha]["num_ventas"] += 1

    serie = []
    for fecha in sorted(dias_map.keys()):
        dd = dias_map[fecha]
        serie.append({
            "fecha": fecha,
            "total": round(dd["total"], 2),
            "ganancia": round(dd["ganancia"], 2),
            "num_ventas": dd["num_ventas"],
        })
    return serie


@app.get("/api/dashboard/top-productos")
def dashboard_top_productos(
    desde: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d = _rango_utc_dash(desde)
    q = db.query(Venta)
    if d:
        q = q.filter(Venta.creado_en >= d)
    ventas = q.all()

    acumulado = {}
    for v in ventas:
        for it in json.loads(v.detalle_json):
            pid = it.get("producto_id")
            if pid is None:
                continue
            if pid not in acumulado:
                acumulado[pid] = {"cantidad": 0.0, "total": 0.0, "nombre": it.get("nombre", "Producto")}
            acumulado[pid]["cantidad"] += it.get("cantidad", 0)
            acumulado[pid]["total"] += it.get("importe", 0)

    ids = list(acumulado.keys())
    info = {}
    if ids:
        rows = db.query(Producto.id, Producto.imagen_url, Producto.marca, Producto.precio_costo).filter(Producto.id.in_(ids)).all()
        info = {r[0]: {"imagen_url": r[1], "marca": r[2], "precio_costo": r[3] or 0} for r in rows}

    resultado = []
    for pid, dprod in acumulado.items():
        i = info.get(pid, {})
        ganancia = dprod["total"] - i.get("precio_costo", 0) * dprod["cantidad"]
        resultado.append({
            "producto_id": pid,
            "nombre": dprod["nombre"],
            "marca": i.get("marca"),
            "imagen_url": i.get("imagen_url"),
            "cantidad_vendida": round(dprod["cantidad"], 3),
            "total_vendido": round(dprod["total"], 2),
            "ganancia": round(ganancia, 2),
        })

    resultado.sort(key=lambda x: x["cantidad_vendida"], reverse=True)
    return resultado[:limit]


@app.get("/dashboard", response_class=FileResponse)
def dashboard_page():
    return FileResponse("static/dashboard.html")

'''
    src = src.rstrip('\n') + '\n' + endpoints + '\n'
    print("   OK endpoints /api/dashboard/resumen, /serie-diaria, /top-productos y ruta /dashboard agregados")

# Guardar main.py SOLO si hubo cambios
if src != original_src:
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(src)

# ================================================================
# 4. Verificar sintaxis de main.py ANTES de reiniciar nada
# ================================================================
print("4. Verificando sintaxis de main.py...")
try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   OK main.py tiene sintaxis valida")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en main.py:")
    print("   Linea " + str(e.lineno) + ": " + str(e.text))
    print("   " + str(e.msg))
    main_ok = False

# ================================================================
# 5. Agregar tile "Dashboard" en el menu principal (solo gerentes)
# ================================================================
print("5. Agregando tile de Dashboard al menu...")
menu_path = os.path.join(STATIC, 'menu.html')
msrc = open(menu_path, encoding='utf-8').read()

if 'href="/dashboard"' in msrc:
    print("   * El tile de Dashboard ya existia, se omite")
else:
    tile = '''  <a class="menu-btn solo-gerente" href="/dashboard" style="display:none">
    <div class="icon icon-pagos">📊</div>
    <div class="menu-text">
      <div class="menu-title">Dashboard</div>
      <div class="menu-desc">Ventas, ganancias y productos mas vendidos</div>
    </div>
    <div class="arrow">›</div>
  </a>

'''
    marcador = '<a class="menu-btn solo-gerente" href="/inventario" style="display:none">'
    if marcador in msrc:
        msrc = msrc.replace(marcador, tile + marcador, 1)
        open(menu_path, 'w', encoding='utf-8').write(msrc)
        print("   OK tile de Dashboard agregado (antes de 'Inventario')")
    else:
        print("   ADVERTENCIA: no se encontro el marcador para insertar el tile en menu.html")
        print("   Agrega manualmente un enlace a /dashboard en el menu.")

# ================================================================
# 6. Reiniciar el servicio SOLO si main.py compila correctamente
# ================================================================
print()
print("=" * 50)
if main_ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Ve al menu principal y entra a 'Dashboard' (Cmd+Shift+R para refrescar).")
else:
    print("NO se reinicio el servicio por el error de sintaxis de arriba.")
    print("Comparte el error para corregirlo antes de reiniciar manualmente con:")
    print("   sudo systemctl restart inventario")
