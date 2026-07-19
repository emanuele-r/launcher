APP_ID  = io.github.lehman.Launcher
PREFIX ?= /usr/local
BINDIR  = $(PREFIX)/bin
DATADIR = $(PREFIX)/share

# Default target is a no-op so `make` (e.g. dh_auto_build) doesn't install.
all:
	@true

install:
	install -Dm755 launcher.py $(DESTDIR)$(BINDIR)/$(APP_ID)
	install -Dm644 home.html $(DESTDIR)$(DATADIR)/$(APP_ID)/home.html
	install -Dm644 $(APP_ID).desktop $(DESTDIR)$(DATADIR)/applications/$(APP_ID).desktop
	install -Dm644 $(APP_ID).metainfo.xml $(DESTDIR)$(DATADIR)/metainfo/$(APP_ID).metainfo.xml
	install -Dm644 $(APP_ID).svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP_ID).svg

uninstall:
	rm -f  $(DESTDIR)$(BINDIR)/$(APP_ID)
	rm -rf $(DESTDIR)$(DATADIR)/$(APP_ID)
	rm -f  $(DESTDIR)$(DATADIR)/applications/$(APP_ID).desktop
	rm -f  $(DESTDIR)$(DATADIR)/metainfo/$(APP_ID).metainfo.xml
	rm -f  $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP_ID).svg

.PHONY: all install uninstall
