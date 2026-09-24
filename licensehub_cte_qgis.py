# -*- coding: utf-8 -*-
"""RUANG SPASIAL License Hub module for CAD Text Extractor QGIS."""
import os
import json
import hashlib

from qgis.PyQt.QtCore import QByteArray, QEventLoop, QTimer, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager

try:
    import winreg
except Exception:
    winreg = None

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

REQUEST_URL = 'https://aktivasi.ruangspasial.my.id/request'
PRODUCT_CODE = 'CDTER'
FIXED_CODE = 'SMI'
PRODUCT_NAME = 'CAD Text Extractor'
TRIAL_LIMIT = 2
LICENSE_FOLDER = 'CAD_TEXT_EXTRACTOR_QGIS_CDTER_SMI'

class LicenseManager(object):
    def __init__(self):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        self.app_dir = os.path.join(appdata, 'RuangSpasial', 'LicenseHub', LICENSE_FOLDER)
        if not os.path.isdir(self.app_dir):
            os.makedirs(self.app_dir)
        self.license_file = os.path.join(self.app_dir, 'license.json')

    def _read_machine_guid(self):
        if winreg is None:
            return ''
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography')
            value, _ = winreg.QueryValueEx(key, 'MachineGuid')
            winreg.CloseKey(key)
            return str(value).strip()
        except Exception:
            return ''

    def get_device_id(self):
        raw = self._read_machine_guid() or 'RUANG_SPASIAL_DEVICE_UNKNOWN'
        return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()[:32]

    def _default_state(self):
        return {
            'product_code': PRODUCT_CODE,
            'fixed_code': FIXED_CODE,
            'activated': False,
            'activation_code': '',
            'trial_used': 0,
            'last_status': 'TRIAL',
            'device_id': self.get_device_id()
        }

    def load_state(self):
        if not os.path.exists(self.license_file):
            return self._default_state()
        try:
            with open(self.license_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = self._default_state()
        for k, v in self._default_state().items():
            data.setdefault(k, v)
        data['product_code'] = PRODUCT_CODE
        data['fixed_code'] = FIXED_CODE
        data['device_id'] = self.get_device_id()
        return data

    def save_state(self, state):
        state['product_code'] = PRODUCT_CODE
        state['fixed_code'] = FIXED_CODE
        state['device_id'] = self.get_device_id()
        with open(self.license_file, 'w') as f:
            json.dump(state, f, indent=2)

    def trial_remaining(self):
        state = self.load_state()
        try:
            used = int(state.get('trial_used', 0))
        except Exception:
            used = 0
        return max(0, TRIAL_LIMIT - used)

    def is_activated_local(self):
        s = self.load_state()
        return bool(s.get('activated', False)) and bool(str(s.get('activation_code', '')).strip()) and \
               str(s.get('product_code', '')).upper() == PRODUCT_CODE and str(s.get('fixed_code', '')).upper() == FIXED_CODE

    def status_text(self):
        s = self.load_state()
        if self.is_activated_local():
            return 'Active - Product %s / Fixed Code %s - Device ID: %s' % (PRODUCT_CODE, FIXED_CODE, self.get_device_id())
        st = str(s.get('last_status', '')).upper()
        if st in ('BLOCKED', 'DEACTIVATED', 'REVOKED', 'INACTIVE_SERVER'):
            return 'Deactivated - License is not active'
        rem = self.trial_remaining()
        if rem > 0:
            return 'Trial - %s of %s uses remaining' % (rem, TRIAL_LIMIT)
        return 'Expired - Trial limit reached'

    def request_url(self):
        params = {
            'device_id': self.get_device_id(),
            'plugin': PRODUCT_CODE,
            'product_code': PRODUCT_CODE,
            'fixed_code': FIXED_CODE,
            'product_name': PRODUCT_NAME
        }
        if urlencode is None:
            return REQUEST_URL + '?device_id=' + self.get_device_id() + '&plugin=' + PRODUCT_CODE + '&product_code=' + PRODUCT_CODE + '&fixed_code=' + FIXED_CODE
        return REQUEST_URL + '?' + urlencode(params)

    def open_request_url(self):
        QDesktopServices.openUrl(QUrl(self.request_url()))

    def _post_json(self, url, payload, timeout=8):
        if not str(url).lower().startswith('https://'):
            return None, 'License Hub requires a verified HTTPS address.'

        reply = None
        try:
            data = json.dumps(payload).encode('utf-8')
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(
                QByteArray(b'Content-Type'), QByteArray(b'application/json'))
            reply = QgsNetworkAccessManager.instance().post(
                request, QByteArray(data))

            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            reply.finished.connect(loop.quit)
            timer.timeout.connect(loop.quit)
            timer.start(max(1, int(timeout)) * 1000)

            run_loop = getattr(loop, 'exec', None)
            if callable(run_loop):
                run_loop()
            else:
                getattr(loop, 'exec' + '_')()

            if not timer.isActive():
                reply.abort()
                return None, 'License Hub request timed out.'
            timer.stop()

            if reply.error():
                return None, reply.errorString() or 'License Hub request failed.'

            raw = bytes(reply.readAll()).decode('utf-8', errors='replace')
            try:
                return json.loads(raw), None
            except (TypeError, ValueError):
                return {'raw': raw}, None
        except Exception as e:
            return None, str(e)
        finally:
            if reply is not None:
                reply.deleteLater()

    def _status_from_response(self, data):
        if not isinstance(data, dict):
            return None, 'Invalid server response.'
        status = str(data.get('status') or data.get('license_status') or data.get('message') or '').strip().upper()
        active_flag = data.get('active')
        approved_flag = data.get('approved')
        if active_flag is True or approved_flag is True or status == 'ACTIVE':
            return True, data.get('message') or 'License active'
        if status in ('PENDING',):
            return False, data.get('message') or 'License request is still pending.'
        if status in ('BLOCKED', 'DEACTIVATED', 'INACTIVE', 'REVOKED', 'REJECTED'):
            return False, data.get('message') or 'License is not active.'
        return None, data.get('message') or 'License status could not be verified.'

    def activate(self, activation_code):
        code = str(activation_code or '').strip().upper()
        if not code:
            return False, 'Enter the activation code first.'
        payload = {
            'product': PRODUCT_CODE,
            'product_code': PRODUCT_CODE,
            'fixed_code': FIXED_CODE,
            'product_name': PRODUCT_NAME,
            'plugin': PRODUCT_CODE,
            'tool': PRODUCT_NAME,
            'device_id': self.get_device_id(),
            'activation_code': code,
            'code': code
        }
        last_msg = ''
        for ep in ['/api/license/validate', '/api/license/status', '/api/activate', '/activate', '/api/license/activate']:
            url = REQUEST_URL.rstrip('/') + ep if not REQUEST_URL.endswith('/request') else REQUEST_URL.rsplit('/request', 1)[0] + ep
            data, err = self._post_json(url, payload)
            if data is not None:
                ok, msg = self._status_from_response(data)
                if ok is True:
                    s = self.load_state()
                    s['activated'] = True
                    s['activation_code'] = code
                    s['last_status'] = 'ACTIVE'
                    self.save_state(s)
                    return True, msg or 'Activation successful.'
                if ok is False:
                    s = self.load_state()
                    s['activated'] = False
                    upper = str(msg).upper()
                    if 'PENDING' in upper:
                        s['last_status'] = 'PENDING'
                    elif 'BLOCK' in upper:
                        s['last_status'] = 'BLOCKED'
                    else:
                        s['last_status'] = 'INACTIVE_SERVER'
                    self.save_state(s)
                    return False, msg or 'License is not active.'
                last_msg = msg or last_msg
            else:
                last_msg = err or last_msg
        return False, 'Activation code could not be verified by License Hub. ' + (last_msg or 'The license synchronization endpoint is not available on the License Hub server.')

    def refresh_activation_from_server(self):
        s = self.load_state()
        code = str(s.get('activation_code', '')).strip().upper()
        if not code:
            return None, 'No activation code is stored locally yet.'
        payload = {
            'product': PRODUCT_CODE,
            'product_code': PRODUCT_CODE,
            'fixed_code': FIXED_CODE,
            'product_name': PRODUCT_NAME,
            'plugin': PRODUCT_CODE,
            'tool': PRODUCT_NAME,
            'device_id': self.get_device_id(),
            'activation_code': code,
            'code': code
        }
        last_msg = ''
        for ep in ['/api/license/status', '/api/license/validate', '/api/activate', '/activate']:
            url = REQUEST_URL.rstrip('/') + ep if not REQUEST_URL.endswith('/request') else REQUEST_URL.rsplit('/request', 1)[0] + ep
            data, err = self._post_json(url, payload)
            if data is not None:
                ok, msg = self._status_from_response(data)
                if ok is True:
                    s['activated'] = True
                    s['last_status'] = 'ACTIVE'
                    self.save_state(s)
                    return True, msg or 'License active.'
                if ok is False:
                    s['activated'] = False
                    upper = str(msg).upper()
                    if 'PENDING' in upper:
                        s['last_status'] = 'PENDING'
                    elif 'BLOCK' in upper:
                        s['last_status'] = 'BLOCKED'
                    else:
                        s['last_status'] = 'INACTIVE_SERVER'
                    self.save_state(s)
                    return False, msg or 'License is not active.'
                last_msg = msg or last_msg
            else:
                last_msg = err or last_msg
        return None, last_msg or 'License status could not be confirmed from the server.'

    def can_run(self):
        if self.is_activated_local():
            ok, msg = self.refresh_activation_from_server()
            if ok is False:
                return False, msg
            return True, 'License is active.'
        if self.trial_remaining() > 0:
            return True, 'Trial mode. Remaining trial: %s of %s.' % (self.trial_remaining(), TRIAL_LIMIT)
        return False, 'Trial has expired. Please activate the license.'

    def consume_trial_for_run(self):
        s = self.load_state()
        if s.get('activated', False):
            return True
        used = int(s.get('trial_used', 0) or 0)
        if used >= TRIAL_LIMIT:
            s['last_status'] = 'TRIAL_EXPIRED'
            self.save_state(s)
            return False
        s['trial_used'] = used + 1
        s['last_status'] = 'TRIAL' if s['trial_used'] < TRIAL_LIMIT else 'TRIAL_EXPIRED'
        self.save_state(s)
        return True
