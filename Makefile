prefix=/usr

all:

clean:
	make -C initramfs clean

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/bin"
	install -m 0755 sysman "$(DESTDIR)/$(prefix)/bin"
	install -m 0755 usrman "$(DESTDIR)/$(prefix)/bin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem"
	find "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem" -type d | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/$(prefix)/libexec/fpemud-refsystem"
	cp -r libexec/* "$(DESTDIR)/$(prefix)/libexec/fpemud-refsystem"
	find "$(DESTDIR)/$(prefix)/libexec/fpemud-refsystem" | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/$(prefix)/share/fpemud-refsystem"
	cp -r data/* "$(DESTDIR)/$(prefix)/share/fpemud-refsystem"
	find "$(DESTDIR)/$(prefix)/share/fpemud-refsystem" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/share/fpemud-refsystem" -type d | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem/initramfs"
	make -C initramfs
	chmod 644 initramfs/init
	chmod 644 initramfs/lvm-lv-activate
	cp initramfs/init "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem/initramfs"
	cp initramfs/lvm-lv-activate "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem/initramfs"

	install -d -m 0755 "$(DESTDIR)/etc/portage/bashrc.d"
	cp "gentoo-bashrc/40-base-patch" "$(DESTDIR)/etc/portage/bashrc.d"
	chmod 644 "$(DESTDIR)/etc/portage/bashrc.d/40-base-patch"

	install -d -m 0755 "$(DESTDIR)/lib/udev/rules.d"
	cp udev/*.rules "$(DESTDIR)/lib/udev/rules.d"

	install -d -m 0755 "$(DESTDIR)/lib/systemd/system"
	install -d -m 0755 "$(DESTDIR)/lib/systemd/system/basic.target.wants"
	install -d -m 0755 "$(DESTDIR)/lib/systemd/system/sysinit.target.wants"
	cp systemd/bless-boot.service "$(DESTDIR)/lib/systemd/system"
	ln -sf "../bless-boot.service" "$(DESTDIR)/lib/systemd/system/basic.target.wants"
	cp systemd/usr-src-linux.service "$(DESTDIR)/lib/systemd/system"
	ln -sf "../usr-src-linux.service" "$(DESTDIR)/lib/systemd/system/sysinit.target.wants"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/src/linux"

uninstall:
	rm -Rf "$(DESTDIR)/$(prefix)/bin/sysman"
	rm -Rf "$(DESTDIR)/$(prefix)/bin/usrman"
	rm -Rf "$(DESTDIR)/$(prefix)/lib64/fpemud-refsystem"
	rm -f  "$(DESTDIR)/etc/portage/bashrc.d/40-base-patch"
	rm -Rf "$(DESTDIR)/lib/udev/rules.d/09-fpemud-refsystem-lvm-fix.rules"

.PHONY: all clean install uninstall
