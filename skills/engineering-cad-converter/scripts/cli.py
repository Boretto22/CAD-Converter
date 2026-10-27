"""Local command interface; never implies engineering certification."""
import argparse
import json
from pathlib import Path

try:
    from . import cad_pipeline as engine, engineering_gate as gate, step_model
except ImportError:
    import cad_pipeline as engine
    import engineering_gate as gate
    import step_model


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version='1.0.0')
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    a = commands.add_parser('inspect')
    a.add_argument('source'); a.add_argument('output')
    a.add_argument('--dpi', type=int, default=200)
    a = commands.add_parser('check'); a.add_argument('model')
    for name in ('build', 'step'):
        a = commands.add_parser(name); a.add_argument('model'); a.add_argument('output')
    a = commands.add_parser('demo'); a.add_argument('output')
    args = p.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = {'version': '1.0.0', 'dependencies': engine.versions(),
                      'step_optional': True, 'recognition': 'agent-assisted; no automatic OCR/CAD recognition'}
        elif args.command == 'inspect':
            result = engine.inspect_source(args.source, args.output, args.dpi)
        elif args.command == 'check':
            result = gate.check(args.model)
        elif args.command == 'build':
            result = gate.build(args.model, args.output)
        elif args.command == 'step':
            result = step_model.build(args.model, args.output)
        else:
            try:
                from .selftest_engineering import main as demo
            except ImportError:
                from selftest_engineering import main as demo
            demo(args.output)
            result = {'output': str(Path(args.output).resolve()), 'synthetic': True}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        p.exit(2, f'BLOQUEADO: {exc}\n')


if __name__ == '__main__':
    main()
