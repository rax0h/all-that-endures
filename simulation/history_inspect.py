"""Read-only archive queries. Run --help; JSON output carries evidence IDs."""
import argparse
import json
from ate_sim.history_archive import HistoryArchive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive')
    sub = p.add_subparsers(dest='query', required=True)
    sub.add_parser('metadata')
    records = sub.add_parser('records'); records.add_argument('kind')
    records.add_argument('--limit', type=int, default=30); records.add_argument('--offset', type=int, default=0)
    person = sub.add_parser('person'); person.add_argument('id', type=int)
    person.add_argument('--limit', type=int, default=30); person.add_argument('--offset', type=int, default=0)
    event = sub.add_parser('event'); event.add_argument('id', type=int)
    causes = sub.add_parser('causes'); causes.add_argument('id', type=int)
    causes.add_argument('--descendants', action='store_true'); causes.add_argument('--limit', type=int, default=1000)
    provenance = sub.add_parser('provenance'); provenance.add_argument('kind'); provenance.add_argument('id')
    timeline = sub.add_parser('settlement'); timeline.add_argument('id', type=int)
    timeline.add_argument('first', type=int); timeline.add_argument('last', type=int)
    timeline.add_argument('--limit', type=int, default=100); timeline.add_argument('--offset', type=int, default=0)
    args = p.parse_args()
    with HistoryArchive(args.archive) as a:
        if args.query == 'metadata': result = a.metadata()
        elif args.query == 'records': result = {'kind': args.kind, 'records': a.records(args.kind, args.limit, args.offset), 'limit': args.limit, 'offset': args.offset}
        elif args.query == 'person': result = a.person(args.id, args.limit, args.offset)
        elif args.query == 'event': result = a.event(args.id) or {'unknown': 'event not recorded'}
        elif args.query == 'causes': result = a.causal_chain(args.id, args.descendants, args.limit)
        elif args.query == 'provenance': result = a.provenance(args.kind, args.id)
        else: result = {'events': a.timeline('settlement', args.id, args.first, args.last, args.limit, args.offset),
                        'coverage': 'recorded event location only; paginated, not inferred residence',
                        'limit': args.limit, 'offset': args.offset}
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == '__main__': main()
