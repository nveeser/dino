%define virtualenv_name dino
%define package_list "Pylons==0.9.7" "SQLAlchemy==0.5.4p2" "Elixir==0.6.1" "MySQL-python==1.2.2" "PyYAML==3.09" "nose==0.10.4"

Version: 1.1
Release: 1

Name: virtualenv-%{virtualenv_name}
Summary: Virtualenv environment: %{virtualenv_name}
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: /mw
BuildArch: x86_64
License: BSD
Url: http://wiki.pylonshq.com/display/pylonscookbook/Using+a+Virtualenv+Sandbox
BuildRequires: mysql-devel
BuildRequires: libyaml-devel
Requires: libyaml

%description
A prebuilt virtualenv environment loaded with pylons:

%{package_list}

%prep
rm -rf %{name}
mkdir -p %{name}
cd %{name}
mkdir -p support-files
wget -q https://svn.metaweb.com/svn/thirdparty/trunk/bootstrap/virtualenv.py 
wget -q https://svn.metaweb.com/svn/thirdparty/trunk/bootstrap/support-files/setuptools-0.6c9-py2.6.egg -O support-files/setuptools-0.6c9-py2.6.egg

%build
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/mw

echo "SETUP VirtualEnv"
python $RPM_BUILD_DIR/virtualenv-pylons/virtualenv.py $RPM_BUILD_ROOT/mw/%{virtualenv_name} 
rm $RPM_BUILD_ROOT/mw/%{virtualenv_name}/lib64
(cd $RPM_BUILD_ROOT/mw/%{virtualenv_name}; ln -s lib lib64)  # This is a small fix to make the path not absolute and point to RPM_BUILD_ROOT

%install

echo "PULLING Pylons"
ARGS="-f https://svn.metaweb.com/svn/thirdparty/trunk --allow-hosts svn.metaweb.com --always-unzip"
$RPM_BUILD_ROOT/mw/%{virtualenv_name}/bin/easy_install $ARGS %{package_list}

set +x
echo "FIXING virtualenv PATHS"
find -H $RPM_BUILD_ROOT/mw/%{virtualenv_name} -type f | while read filename; do    
     perl -p -i.bak -e "s|${RPM_BUILD_ROOT}||g" ${filename}     
     if [ -f ${filename}.bak ]; then
     	rm -f ${filename}.bak
     	echo "FIXED ${filename}"			
     fi
done
set -x

%clean
rm -rf $RPM_BUILD_ROOT  

%files 
%defattr(-,root,root)
/mw/%{virtualenv_name}

