# pulsarpub

Custom websites without too much suffering.

## Development

This is a standard [Django](https://docs.djangoproject.com/) application with
[uv](https://github.com/astral-sh/uv).

1. Set up a new postgresql database called `pulsar` with a user `pulsar` and no
password.

2. Setup environment variables with:

```sh
cp .envrc.example .envrc
source .envrc
```

3. Create database tables with:

```sh
uv run manage.py migrate
```

4. Run development server with:

```sh
uv run manage.py runserver
```

## Format and lint

Run Python formatting with:

```sh
uv run ruff format
```

Run Python linting with:

```sh
uv run ruff check --fix
```

Run Djade Django HTML formatting with:

```sh
uv run djade main/templates/**/*.html
```

## Deploy

Every commit on branch `main` auto-deploys using GitHub Actions.

## Self-host

### 1. Set up domain and DNS

1. Get a domain name eg. example.com
1. Get a server with an IP eg 142.250.187.238
1. Ensure server access over ssh with the root user, eg. `ssh root@142.250.187.238`
1. Set DNS records
    a. One A record at the root domain, pointing to your domain, eg. `example.com` -> `142.250.187.238`
    a. And one A record at the wildcard subdomain, eg `*.example.com` -> `142.250.187.238`

### 2. Set up uv and clone

```sh
# install uv: https://github.com/astral-sh/uv?tab=readme-ov-file#installation
curl -LsSf https://astral.sh/uv/install.sh | sh

# clone
git clone https://github.com/sirodoht/pulsarpub
cd pulsarpub/
```

### 3. Set up ansible

```sh
cp ansible/.envrc.example ansible/.envrc

# edit ansible/.envrc with your details
# ANSIBLE_HOST should be your server IP
# DOMAIN_NAME your domain name
# SECRET_KEY a random string of ~50 chars and symbols
# POSTGRES_PASSWORD a >20 char password
# DATABASE_URL change the password to be same as POSTGRES_PASSWORD
vim ansible/.envrc

uv sync
cd ansible/
uv run ansible-playbook -v playbook.yaml
```

### 4. Done

That's it. Open your browser and visit your pulsar instance at your domain. It should
take a few seconds to generate the TLS certificate the first time.

## License

Symbolic Public License
