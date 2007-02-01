%define release 0.1
%define __python python
%define pythonversion 2.3
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:             bcfg2
Version:          0.9.1a
Release: %{release}
Summary:          Configuration management system

Group:            Applications/System
License:          BSD
URL:              http://trac.mcs.anl.gov/projects/bcfg2
Source0:          ftp://ftp.mcs.anl.gov/pub/bcfg/bcfg2-%{version}.tar.gz
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:        noarch

BuildRequires:    python-devel
Requires:         lxml >= 0.9

%description
Bcfg2 helps system administrators produce a consistent, reproducible,
and verifiable description of their environment, and offers
visualization and reporting tools to aid in day-to-day administrative
tasks. It is the fifth generation of configuration management tools
developed in the Mathematics and Computer Science Division of Argonne
National Laboratory.

It is based on an operational model in which the specification can be
used to validate and optionally change the state of clients, but in a
feature unique to bcfg2 the client's response to the specification can
also be used to assess the completeness of the specification. Using
this feature, bcfg2 provides an objective measure of how good a job an
administrator has done in specifying the configuration of client
systems. Bcfg2 is therefore built to help administrators construct an
accurate, comprehensive specification.

Bcfg2 has been designed from the ground up to support gentle
reconciliation between the specification and current client states. It
is designed to gracefully cope with manual system modifications.

Finally, due to the rapid pace of updates on modern networks, client
systems are constantly changing; if required in your environment,
Bcfg2 can enable the construction of complex change management and
deployment strategies.

%package -n bcfg2-server
Version: %{version}
Summary: Bcfg2 Server
Group: System Tools
Requires: bcfg2, pyOpenSSL
%if "%{_vendor}" == "redhat"
Requires: gamin-python
%endif


%description -n bcfg2-server
Bcfg2 client

%prep
%setup -q

%build
%{__python}%{pythonversion} setup.py build

%install
%{__python}%{pythonversion} setup.py install --root=%{buildroot} --record=INSTALLED_FILES
%{__install} -d %{buildroot}%{_bindir}
%{__install} -d %{buildroot}%{_sbindir}
%{__install} -d %{buildroot}%{_initrddir}
%{__install} -d %{buildroot}%{_sysconfdir}/default
%{__install} -d %{buildroot}%{_sysconfdir}/cron.daily
%{__install} -d %{buildroot}%{_sysconfdir}/cron.hourly
%{__install} -d %{buildroot}%{_prefix}/lib/bcfg2
%{__mv} %{buildroot}/usr/bin/bcfg2* %{buildroot}%{_sbindir}
%{__install} -m 755 debian/buildsys/common/bcfg2.init %{buildroot}%{_initrddir}/bcfg2
%{__install} -m 755 debian/buildsys/common/bcfg2-server.init %{buildroot}%{_initrddir}/bcfg2-server
%{__install} -m 755 debian/bcfg2.default %{buildroot}%{_sysconfdir}/default/bcfg2
%{__install} -m 755 debian/bcfg2.cron.daily %{buildroot}%{_sysconfdir}/cron.daily/bcfg2
%{__install} -m 755 debian/bcfg2.cron.hourly %{buildroot}%{_sysconfdir}/cron.hourly/bcfg2
%{__install} -m 755 tools/bcfg2-cron %{buildroot}%{_prefix}/lib/bcfg2/bcfg2-cron

%clean
[ "%{buildroot}" != "/" ] && %{__rm} -rf %{buildroot} || exit 2

%files -n bcfg2
%defattr(-,root,root,-)
%{_sbindir}/bcfg2
%{python_sitelib}/Bcfg2/*.py*
%{python_sitelib}/Bcfg2/Client/*
%{_mandir}/man1/*
%{_mandir}/man5/*
%{_initrddir}/bcfg2
%config(noreplace) %{_sysconfdir}/default/bcfg2
%{_sysconfdir}/cron.hourly/bcfg2
%{_sysconfdir}/cron.daily/bcfg2
%{_prefix}/lib/bcfg2/bcfg2-cron

%post -n bcfg2-server
/sbin/chkconfig --add bcfg2-server

%files -n bcfg2-server
%defattr(-,root,root,-)

%{_initrddir}/bcfg2-server

%{python_sitelib}/Bcfg2/Server

%{_datadir}/bcfg2

%{_sbindir}/bcfg2-admin
%{_sbindir}/bcfg2-build-reports
%{_sbindir}/bcfg2-info
%{_sbindir}/bcfg2-ping-sweep
%{_sbindir}/bcfg2-query
%{_sbindir}/bcfg2-repo-validate
%{_sbindir}/bcfg2-server

%{_mandir}/man8/*.8*
%dir %{_prefix}/lib/bcfg2

%changelog
* Fri Feb 2 2007 Mike Brady <mike.brady@devnull.net.nz> 0.9.1
- Removed use of _libdir due to Red Hat x86_64 issue.

* Fri Dec 22 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-5
- Server needs client library files too so put them in main package

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-4
- Yes, actually we need to require openssl

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-3
- Don't generate SSL cert in post script, it only needs to be done on
  the server and is handled by the bcfg2-admin tool.
- Move the /etc/bcfg2.key file to the server package
- Don't install a sample copy of the config file, just ghost it
- Require gamin-python for the server package
- Don't require openssl
- Make the client a separate package so you don't have to have the
  client if you don't want it

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-2
- Add more documentation

* Mon Dec 18 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-1
- First version for Fedora Extras

* Fri Sep 15 2006 Narayan Desai <desai@mcs.anl.gov> - 0.8.4-1
- Initial log

