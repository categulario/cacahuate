from .base import BaseAuthProvider
from ldap3 import Server, Connection, ALL, NTLM, core
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError
from pvm.errors import AuthenticationError
from pvm.http.wsgi import app
import sys


class LdapAuthProvider(BaseAuthProvider):

    def authenticate(self, credentials):
        if 'username' not in credentials or \
           'password' not in credentials:
            raise AuthenticationError

        domain = app.config['LDAP_DOMAIN']
        if 'domain' in credentials:
            domain = credentials['domain']

        username = '{domain}\\{username}'.format(
            domain=domain,
            username=credentials['username'],
        )

        password = credentials['password']

        server = Server(
            app.config['LDAP_URI'],
            get_info=ALL,
            use_ssl=app.config['LDAP_SSL'],
        )

        print(username)
        print(password)

        try:
            conn = Connection(
                server,
                user=username,
                password=password,
                auto_bind=True,
                authentication=NTLM,
            )
        except LDAPBindError:
            print("ldap", "wrong credentials")
            raise AuthenticationError
        except LDAPSocketOpenError:
            print("ldap", "connection error")
            raise AuthenticationError
        except:
            print("ldap", sys.exc_info()[0])
            raise AuthenticationError

        return {
            'identifier': 'ldap/' + username,
        }
