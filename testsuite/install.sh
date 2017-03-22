#!/bin/bash -ex

# install script for Travis-CI
PYVER=$(python -c 'import sys;print(".".join(str(v) for v in sys.version_info[0:2]))')

if [[ ${PYVER:0:1} == "2" && $PYVER != "2.7" && $PYVER != "2.6" ]]; then
    pip install -r testsuite/requirements-legacy.txt
else
    pip install --upgrade pip

    pip_wheel() {
        pip wheel --find-links="$HOME/.cache/wheels/" --wheel-dir="$HOME/.cache/wheels/" "$@"
        pip install --no-index --find-links="$HOME/.cache/wheels/" "$@"
    }

    pip_wheel -r testsuite/requirements.txt

    if [[ $PYVER == "2.6" ]]; then
        pip_wheel unittest2
    fi

    if [[ "$WITH_OPTIONAL_DEPS" == "yes" ]]; then
        pip_wheel PyYAML pyinotify boto pylibacl Jinja2 mercurial guppy \
            cherrypy python-augeas nose-show-skipped

        if [[ ${PYVER:0:1} == "2" ]]; then
            pip_wheel cheetah m2crypto
    
            if [[ $PYVER != "2.7" ]]; then
                pip_wheel 'django<1.7' 'South<0.8'
            else
                pip_wheel django
            fi
        fi
    fi
fi

# Setup the local xml schema cache
download_schema() {
    if [[ ! -e "$1" ]]; then
        wget -O "$1" "$2"
    fi
}

mkdir -p "$HOME/.cache/xml/"
download_schema "$HOME/.cache/xml/XMLSchema.xsd" "http://www.w3.org/2001/XMLSchema.xsd"
download_schema "$HOME/.cache/xml/xml.xsd" "http://www.w3.org/2001/xml.xsd"

cat > "$HOME/.cache/xml/catalog.xml" <<EOF
<?xml version="1.0"?>
<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">
  <system systemId="http://www.w3.org/2001/XMLSchema.xsd" uri="$HOME/.cache/xml/XMLSchema.xsd" />
  <system systemId="http://www.w3.org/2001/xml.xsd" uri="$HOME/.cache/xml/xml.xsd" />
  <nextCatalog catalog="/etc/xml/catalog.xml" />
</catalog>
EOF
