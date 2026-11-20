#!/usr/bin/env python3
"""NUMERIS v0.5 — offline symbolic relational oracle (Python 3.9+)."""
import hashlib
import json
import sqlite3
import math
import secrets
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

JOURNAL = Path.home() / '.numeris' / 'journal.jsonl'
POSITIONS = ('Present', 'Hidden Influence', 'Direction')
ARCHETYPES = {
    1: ('Monad', 'unity', 'initiative', 'isolation', 'emergence'),
    2: ('Mirror', 'duality', 'cooperation', 'division', 'reconciliation'),
    3: ('Voice', 'creation', 'expression', 'distraction', 'synthesis'),
    4: ('Foundation', 'structure', 'stability', 'rigidity', 'reconstruction'),
    5: ('Wanderer', 'change', 'freedom', 'instability', 'adaptation'),
    6: ('Guardian', 'harmony', 'responsibility', 'overattachment', 'restoration'),
    7: ('Seeker', 'mystery', 'contemplation', 'withdrawal', 'revelation'),
    8: ('Sovereign', 'power', 'mastery', 'domination', 'rebalancing'),
    9: ('Sage', 'completion', 'wisdom', 'exhaustion', 'renewal'),
}
ASPECTS = ('essential', 'constructive', 'shadow', 'transformative')


def digital_root(value):
    if value < 1:
        raise ValueError('Digital root requires a positive integer')
    return 1 + (value - 1) % 9


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, math.isqrt(n) + 1))


def relationships(numbers):
    a, b, c = numbers
    result = []
    for i, j in ((0, 1), (1, 2), (0, 2)):
        x, y = numbers[i], numbers[j]
        if x == y:
            kind, label = 'resonance', 'identical values'
        elif math.gcd(x, y) > 1:
            kind, label = 'harmony', f'shared factor {math.gcd(x, y)}'
        elif x % 2 != y % 2:
            kind, label = 'polarity', 'opposite parity'
        else:
            kind, label = 'independence', 'coprime values of the same parity'
        result.append({'indices': [i, j], 'kind': kind, 'detail': label})
    if a < b < c:
        movement = 'ascension'
    elif a > b > c:
        movement = 'descent'
    elif a == c:
        movement = 'equilibrium'
    else:
        movement = 'mixed'
    return result, movement


QUESTIONS = {
    1: 'What would you choose if you could take just one step?',
    2: 'Whose perspective would change how you see this?',
    3: 'What needs a voice, and how might you give it one?',
    4: 'What could you put in place that would still help tomorrow?',
    5: 'Where would a small experiment give you room to move?',
    6: 'What kind of care would make a difference here?',
    7: 'What might you notice if you left the question open a little longer?',
    8: 'Where can you use your influence with a lighter hand?',
    9: 'What has run its course, and what can you carry forward?',
}


def synthesis_passage(entries, movement, root):
    present, hidden, direction = (entry['meaning'] for entry in entries)
    if movement == 'ascension':
        passage = (f'Begin with {present}. As the numbers rise, consider how '
                   f'{hidden} might help you grow toward {direction}.')
    elif movement == 'descent':
        passage = (f'Begin with {present} and trace it back to {hidden}. '
                   f'What might fall away to make room for {direction}?')
    elif movement == 'equilibrium':
        passage = (f'You return to the number you began with. Read {present} '
                   f'again through the lens of {hidden}. What does {direction} look like now?')
    else:
        passage = (f'Hold {present} alongside {hidden}. Where those two meet, '
                   f'look for an opening toward {direction}.')
    return f'{passage} {QUESTIONS[root]}'


def analyze(numbers):
    if len(numbers) != 3 or any(type(n) is not int or not 1 <= n <= 9 for n in numbers):
        raise ValueError('Expected exactly three integers from 1 through 9')
    links, movement = relationships(numbers)
    counts = Counter(numbers)
    entries = []
    for index, n in enumerate(numbers):
        # Scores are a declared symbolic convention, not statistical probabilities.
        scores = {'essential': 2, 'constructive': 0, 'shadow': 0, 'transformative': 0}
        reasons = {aspect: [] for aspect in ASPECTS}

        def add(aspect, points, reason):
            scores[aspect] += points
            reasons[aspect].append(f'+{points} {reason}')

        if index == 0:
            add('essential', 1, 'Present position')
        elif index == 1:
            add('shadow', 1, 'Hidden Influence position')
        else:
            add('transformative', 1, 'Direction position')
        if index == 1 and counts[n] > 1:
            add('shadow', 4, 'a repeated hidden influence can become a blind spot')
        reasons['essential'].insert(0, '+2 baseline archetypal meaning')
        if is_prime(n):
            add('essential', 1, 'prime number')
        if n in (1, 4, 9):
            add('constructive', 1, 'perfect square')
        for link in links:
            if index not in link['indices']:
                continue
            if link['kind'] == 'resonance':
                add('constructive', 2, 'resonance with another position')
                add('shadow', 1, 'possible overemphasis through repetition')
            elif link['kind'] == 'harmony':
                add('constructive', 2, 'shared factor with another position')
            elif link['kind'] == 'polarity':
                add('transformative', 2, 'polarity with another position')
            else:
                add('essential', 1, 'independence from another position')
        if movement == 'ascension':
            add('transformative', 2, 'ascending sequence')
        elif movement == 'descent':
            add('shadow', 2, 'descending sequence')
        elif movement == 'equilibrium':
            add('constructive', 2, 'return to opening value')
        # Fixed tie priority keeps identical casts perfectly reproducible.
        aspect = max(ASPECTS, key=lambda key: scores[key])
        name, essence, constructive, shadow, transformative = ARCHETYPES[n]
        meanings = dict(zip(ASPECTS, (essence, constructive, shadow, transformative)))
        entries.append({'position': POSITIONS[index], 'number': n, 'name': name,
                        'aspect': aspect, 'meaning': meanings[aspect],
                        'scores': scores, 'reasons': reasons[aspect] or ['baseline archetypal meaning']})
    synthesis = digital_root(sum(numbers))
    return {'numbers': list(numbers), 'sum': sum(numbers), 'synthesis': synthesis,
            'synthesis_name': ARCHETYPES[synthesis][0],
            'passage': synthesis_passage(entries, movement, synthesis),
            'synthesis_meaning': ARCHETYPES[synthesis][1],
            'relationships': links, 'movement': movement, 'analyses': entries,
            'repeats': {str(n): count for n, count in counts.items() if count > 1}}


def cast():
    # The three independent secure draws occur only after Enter is pressed.
    nums = [secrets.randbelow(9) + 1 for _ in range(3)]
    return {'timestamp': datetime.now(timezone.utc).isoformat(),
            'question': None, 'version': '0.5',
            'method': 'three independent OS-entropy-backed draws, 1-9', **analyze(nums)}


def display(record):
    print('\n' + '=' * 58)
    print(f"NUMERIS v{record.get('version', '?')} | RELATIONAL ORACLE")
    print('=' * 58)
    print('Unspoken intention | Cast:', ' - '.join(map(str, record['numbers'])))
    print('\nRELATIONSHIPS')
    for link in record['relationships']:
        i, j = link['indices']
        print(f"  {POSITIONS[i]} ↔ {POSITIONS[j]}: {link['kind']} ({link['detail']})")
    print('  Sequence:', record['movement'])
    print('\nARCHETYPES')
    for item in record['analyses']:
        print(f"\n  {item['position']}: {item['number']} — The {item['name']}")
        print(f"  {item['aspect'].title()}: {item['meaning'].capitalize()}")
        print('  Selection:', '; '.join(item['reasons']))
        print('  Scores:', ', '.join(f'{k}={v}' for k, v in item['scores'].items()))
    print(f"\nSYNTHESIS: {record['sum']} → {record['synthesis']} — The {record['synthesis_name']}")
    print('  Integrating principle:', record['synthesis_meaning'].capitalize())
    if record.get('passage'):
        print(' ', record['passage'])
    print('\nUse the symbols to reflect on your private question.')
    print('These correspondences are interpretive, not verified predictions.')


def save(record):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open('a', encoding='utf-8') as file:
        file.write(json.dumps(record, ensure_ascii=False) + '\n')
    print('Saved to', JOURNAL)


def review(record):
    try:
        display(record)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        print('This entry has a partial or older format. Its saved contents follow.')
        print(json.dumps(record, indent=2, ensure_ascii=False))

    # A separate notebook lets even v0.4 keep reading the original journal.
    snapshot = json.dumps(record, sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(snapshot.encode('utf-8')).hexdigest()
    notebook = JOURNAL.with_name('reflections.sqlite3')
    with_notes = 'SELECT stamp, body FROM notes WHERE reading = ? ORDER BY rowid'
    schema = 'CREATE TABLE IF NOT EXISTS notes (reading TEXT, stamp TEXT, body TEXT)'
    with closing(sqlite3.connect(notebook)) as db:
        db.execute(schema)
        for stamp, body in db.execute(with_notes, (key,)):
            print(f'  {stamp} | {body}')
        note = input('Add a reflection (Enter to go back): ').strip()
        if note:
            with db:
                db.execute('INSERT INTO notes VALUES (?, ?, ?)',
                           (key, datetime.now(timezone.utc).isoformat(), note))
            print('Reflection saved.')


def history():
    if not JOURNAL.exists():
        print('No saved consultations.')
        return
    records = []
    with JOURNAL.open(encoding='utf-8') as file:
        for line in file:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
                else:
                    print('Skipped a damaged journal entry.')
            except json.JSONDecodeError:
                print('Skipped a damaged journal entry.')
    if not records:
        print('No saved consultations.')
        return
    records.reverse()
    offset = 0
    while True:
        page = records[offset:offset + 10]
        print(f'\nJournal | {len(records)} saved | newest first')
        for number, entry in enumerate(page, offset + 1):
            print(f"{number}. {str(entry.get('timestamp', '?'))[:16]} | "
                  f"{entry.get('numbers', '?')} → {entry.get('synthesis', '?')}")
        choice = input('Reading number, [o]lder, [n]ewer, or Enter to leave: ').strip().lower()
        if not choice:
            return
        if choice == 'o' and offset + 10 < len(records):
            offset += 10
        elif choice == 'n' and offset:
            offset -= 10
        elif choice in {str(i) for i in range(offset + 1, offset + len(page) + 1)}:
            review(records[int(choice) - 1])
        else:
            print('Choose a displayed reading or an available page.')


def confirm_save():
    while True:
        answer = input('\nSave this casting? [Y/n]: ').strip().lower()
        if answer in ('', 'y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        print('Enter yes or no.')


def main():
    while True:
        print('\n=== NUMERIS v0.5 ===\n1. Silent casting\n2. Journal\n3. Exit')
        choice = input('Select: ').strip()
        if choice == '1':
            print('\nStill your mind. Hold your question silently.')
            input('When ready, press Enter to cast...')
            record = cast()
            display(record)
            if confirm_save():
                save(record)
        elif choice == '2':
            history()
        elif choice == '3':
            print('Session ended.')
            return
        else:
            print('Choose 1, 2, or 3.')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nSession ended.')
    except (OSError, sqlite3.Error) as error:
        print('Storage error:', error)
