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


### 5. Stripe Configuration

Once done, you can also enable premium subscriptions. Pulsar supports Stripe.

1. Create a [Stripe account](https://dashboard.stripe.com/register)
2. Get your API keys from the Stripe Dashboard
3. Create a subscription product and get the price ID
4. Add the following environment variables to your `.envrc` file:

```sh
export STRIPE_PUBLISHABLE_KEY=pk_test_...
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export STRIPE_PRICE_ID=price_...
```

5. Set up a webhook endpoint in Stripe Dashboard pointing to `/webhooks/stripe/`
6. Configure the webhook to listen for these events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

## License

Copyright pulsarpub Contributors

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU Affero General Public License as published by the Free Software Foundation,
version 3.
