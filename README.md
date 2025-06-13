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

Every commit on branch `main` auto-deploys using GitHub Actions. To deploy manually:

```sh
cd ansible/
cp .envrc.example .envrc
uv run ansible-playbook -v playbook.yaml
```

## License

Symbolic Public License
