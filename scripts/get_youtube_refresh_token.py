#!/usr/bin/env python3
import argparse, json, urllib.parse, urllib.request, urllib.error

AUTH = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/youtube.upload'
REDIRECT = 'http://localhost/'

def ask(label):
    return input(label + ': ').strip()

def main():
    p = argparse.ArgumentParser(description='Get YouTube OAuth refresh token')
    p.add_argument('--client-id')
    p.add_argument('--client-secret')
    p.add_argument('--code')
    a = p.parse_args()

    client_id = a.client_id or ask('YOUTUBE_CLIENT_ID')
    client_secret = a.client_secret or ask('YOUTUBE_CLIENT_SECRET')

    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT,
        'response_type': 'code',
        'scope': SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
    }
    url = AUTH + '?' + urllib.parse.urlencode(params)

    print('\n1) Open this URL and approve access:\n')
    print(url)
    print('\n2) After approval, copy the code from the redirected URL.')
    code = a.code or ask('\nAuthorization code')

    data = urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT,
    }).encode()

    req = urllib.request.Request(TOKEN, data=data, method='POST')
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(e.read().decode())
        raise

    refresh = result.get('refresh_token')
    if not refresh:
        print(json.dumps(result, indent=2))
        raise SystemExit('No refresh_token returned. Retry with prompt=consent.')

    print('\nAdd these GitHub Repository Secrets:\n')
    print('YOUTUBE_CLIENT_ID=' + client_id)
    print('YOUTUBE_CLIENT_SECRET=' + client_secret)
    print('YOUTUBE_REFRESH_TOKEN=' + refresh)

if __name__ == '__main__':
    main()
