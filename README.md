# Billie the Platypus

Billie judges your terminal. Silently. With disdain.

A judgmental platypus who has opinions about your cloud bill, your inbox, and your life choices. Inspired by [doge](https://github.com/thiderman/doge).

## Install

```bash
uv tool install git+https://github.com/quinnypig/billie.git
```

Or with pip:

```bash
pip install git+https://github.com/quinnypig/billie.git
```

## Usage

```bash
billie
```

Pipe things into Billie for personalized judgment:

```bash
cat your-awful-code.py | billie
```

### Options

```
--no-billie        Hide the platypus (but why)
-mh, --max-height  Max terminal height
-mw, --max-width   Max terminal width
-d, --density      Word density percent (0-100, default 30)
```

## Who is Billie?

Billie is Corey Quinn's long-suffering platypus executive assistant. He manages his calendar, triages his inbox, and has strong feelings about your AWS bill. He is tired. He has seen things. The answer is still no.

## License

MIT
