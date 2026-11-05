"""Locate quoted original spans once; numeric interpretation belongs to observed_conversion."""
from __future__ import annotations

import hashlib
import csv
from pathlib import Path
import re

from physicsguard.schema.observed_conversion import read_source_value
from physicsguard.core.units import read_unit, known_conversion, is_transducer_output


def header_unit(label: str) -> str | None:
    """Read a table/CSV header through the same unit table as observation conversion."""
    bracket = re.search(r'[\[(]([^\])]+)[\])]\s*$', label)
    tokens = label.split('_')
    candidates = ([bracket.group(1)] if bracket else []) + [
        '/'.join(tokens[i:]) for i in range(1 if len(tokens) > 1 else 0, len(tokens))]
    return next((u for u in candidates if read_unit(u) is not None or is_transducer_output(u)), None)


def _table_span(quote: dict, text: str) -> str | None:
    hits, block = [], []
    for line in text.splitlines()+['']:
        if line.strip().startswith('|'):
            block.append([c.strip() for c in line.strip().strip('|').split('|')])
            continue
        rule = next((i for i, r in enumerate(block) if r and all(re.fullmatch(r':?-+:?', c) for c in r)), None)
        if rule is not None and rule:
            headers = block[:rule]
            width = max(map(len, headers))
            filled = []
            for depth, row in enumerate(headers):
                row = row + ['']*(width-len(row))
                if depth < len(headers)-1:
                    for i in range(1, width):
                        row[i] = row[i] or row[i-1]
                filled.append(row)
            labels = [' / '.join(dict.fromkeys(r[i] for r in filled if r[i])) for i in range(width)]
            columns = [i for i, label in enumerate(labels) if quote.get('column', '') in label]
            for row in block[rule+1:]:
                if row and row[0] == quote.get('row') and len(columns) == 1 and columns[0] < len(row):
                    i = columns[0]
                    hits.append(row[i] + ' ' + (header_unit(labels[i]) or ''))
        block = []
    return hits[0].strip() if len(hits) == 1 else None


def load_sources(declared: dict, base: Path) -> dict:
    sources = {}
    for name, filename in declared.items():
        content = (base / filename).read_bytes()
        sources[name] = {'text': content.decode('utf-8'), 'path': str(filename),
                         'digest': hashlib.sha256(content).hexdigest()}
    return sources


def find_quote(quote: dict, sources: dict) -> tuple[str | None, str | None, str]:
    source = sources.get(quote.get('from'))
    if source is None:
        return None, None, 'quote_not_in_source: source is not declared'
    if 'row' in quote:
        span = _table_span(quote, source['text'])
        return (span, source['digest'], '') if span is not None else (
            None, source['digest'], 'quote_not_in_source: table row/column is absent or ambiguous')
    text = quote.get('text')
    if not isinstance(text, str) or not text.strip():
        return None, source['digest'], 'quote_not_in_source: a nonempty text quote is required'
    pattern = r'\s+'.join(re.escape(token) for token in text.split())
    matched = re.search(pattern, source['text'])
    if matched is None:
        return None, source['digest'], f'quote_not_in_source: {text!r}'
    return matched.group(), source['digest'], ''


def source_row(identifier: str, quote: dict | None, ai_value: float | None,
               unit: str | None, sources: dict, properties: dict | None = None) -> tuple[dict, dict]:
    row = {'id': identifier, 'colour': 'grey', 'reason': 'AI value unchecked: no source quote',
           'source_digest': None, 'value': ai_value, 'unit': unit, 'tolerance': None}
    if quote is None:
        return row, {'kind': 'unreadable'}
    span, digest, problem = find_quote(quote, sources)
    row['source_digest'] = digest
    if problem:
        row.update(colour='red', reason=problem)
        return row, {'kind': 'unreadable'}
    reading = read_source_value(span, unit, properties)
    row['tolerance'] = reading.get('tolerance')
    if reading['kind'] == 'unreadable':
        row['reason'] = 'AI value unchecked: ' + reading['reason']
    elif reading['kind'] == 'range':
        lo, hi, tol = reading['lower'], reading['upper'], reading['tolerance']
        inside = ai_value is not None and lo-tol <= ai_value <= hi+tol
        row.update(colour='green' if inside else 'red', lower=lo, upper=hi,
                   reason='inside; the AI chose the point' if inside else 'source_reading_disagrees: outside the range')
    else:
        value, tol = reading['value'], reading['tolerance']
        agrees = ai_value is not None and abs(ai_value-value) <= tol
        ratio = ai_value/value if ai_value is not None and value else float('inf')
        row.update(colour='green' if agrees else 'red', value=value,
                   reason=reading['reason'] if agrees else
                   f'source_reading_disagrees: source {value:g} {unit or ""}, AI {ai_value}, x{ratio:.4g}')
    return row, reading


def prepare_properties(observed, sources: dict) -> list[dict]:
    rows = []
    for name, prop in observed.properties.items():
        row, reading = source_row('property:' + name, prop.quote, prop.value, prop.unit, sources)
        rows.append(row)
        if reading['kind'] == 'value':
            prop.value = reading['value']
    return rows


def check_source_rows(observed, sources: dict, rows: list[dict]) -> None:
    property_rows = {r['id'].removeprefix('property:'): r for r in rows}
    for name, value in observed.variables.items():
        existing = next((r for r in rows if r['id'] == name), None)
        if existing is not None:
            from physicsguard.schema.observed_conversion import _conversion_routes
            routes = _conversion_routes(existing['unit'], value.unit, observed.properties)
            conversion = routes[0] if len(routes) == 1 else None
            if conversion is None and is_transducer_output(existing['unit']) and value.conversion_factor is not None:
                conversion = (value.conversion_factor, value.conversion_offset or 0.)
            if conversion and existing.get('tolerance') is not None:
                existing['tolerance'] *= abs(conversion[0])
            claimed = existing.pop('asserted_value', None)
            if claimed is not None and existing.get('tolerance') is not None and abs(claimed-value.value) > existing['tolerance']:
                existing.update(colour='red', reason=f'source_reading_disagrees: source {value.value:g}, AI {claimed:g}')
            existing.update(value=value.value, unit=value.unit)
            if value._conversion_checked is False and existing['colour'] == 'green':
                existing.update(colour='grey', reason='AI value unchecked: CSV conversion uses a calibration the tool cannot verify')
            continue
        row, reading = source_row(name, value.quote, value.value, value.unit, sources, observed.properties)
        if reading['kind'] == 'value':
            value.value = reading['value']
            # Subsequent copies use the source value without reapplying an AI's old conversion.
            value.raw_value = value.raw_unit = value.conversion_property = None
        if reading['kind'] in ('value', 'range') and row['colour'] == 'green':
            # A declared but unquoted property is a usable hypothesis, not source evidence.
            from physicsguard.schema.observed_conversion import _signal_readings
            found = _signal_readings(find_quote(value.quote, sources)[0]).readings if value.quote else []
            if found and known_conversion(found[0].unit, value.unit or '1') is None:
                from physicsguard.core.units import property_link
                used = [p for p, prop in observed.properties.items() if
                        property_link(found[0].unit, value.unit or '1', prop.value, prop.unit) is not None]
                if not used or any(property_rows[p]['colour'] != 'green' for p in used):
                    row.update(colour='grey', reason='AI value unchecked: conversion uses an unquoted property')
        rows.append(row)
    observed._source_readings = rows
    observed._sources = sources


def prepare_csv_rows(observed, sources: dict, base: Path) -> list[dict]:
    rows, files = [], {}
    for name, value in observed.variables.items():
        match = re.fullmatch(r'(.+)@(\d+)', value.external_signal or '')
        if (value.source or '').endswith('.csv') and match:
            files.setdefault(value.source, []).append((name, value, match.group(1), int(match.group(2))))
    for filename, mappings in files.items():
        path = base / filename
        if not path.is_file():
            rows.extend({'id': name, 'colour': 'grey', 'reason': f'AI value unchecked: source file unavailable: {filename}',
                         'source_digest': None, 'value': value.value, 'unit': value.unit, 'tolerance': None}
                        for name, value, _, _ in mappings)
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        with path.open(encoding='utf-8', newline='') as handle:
            table = list(csv.DictReader(handle))
        sources['csv:' + filename] = {'path': filename, 'digest': digest, 'text': ''}
        base_row = min(m[3] for m in mappings)
        shift = 0
        key = observed.row_key
        if key and key.get('file') == filename:
            unit = header_unit(key['field'])
            if key.get('quote'):
                span, _, problem = find_quote(key['quote'], sources)
                got = read_source_value(span, unit) if not problem and unit else {'kind': 'unreadable'}
            else:
                got = {'kind': 'value', 'value': key['value'], 'tolerance': 1e-12}
            selected = [i for i, row in enumerate(table) if got['kind'] == 'value' and
                        abs(float(row[key['field']])-got['value']) <= got['tolerance']]
            if len(selected) == 1:
                shift = selected[0]-base_row
            okay = len(selected) == 1 and not shift
            rows.append({'id': 'row:' + filename, 'colour': 'green' if okay else 'red',
                         'reason': f'row_key: {key["field"]}; source rows {selected}, snapshot row {base_row}',
                         'source_digest': digest})
        else:
            rows.append({'id': 'row:' + filename, 'colour': 'grey',
                         'reason': 'row chosen by the AI: no row_key quote', 'source_digest': digest})
        for name, value, field, index in mappings:
            raw = float(table[index+shift][field])
            unit = header_unit(field)
            calibrated = is_transducer_output(value.raw_unit) and value.conversion_factor is not None
            same = unit is None or known_conversion(unit, value.raw_unit) == (1.0, 0.0)
            equal = value.raw_value is not None and abs(value.raw_value-raw) <= max(abs(raw)*1e-3, 1e-12)
            colour = 'grey' if calibrated and equal else ('green' if same and equal and unit else ('red' if not same or not equal else 'grey'))
            reason = (f'header unit {unit}, snapshot unit {value.raw_unit}' if not same else
                      f'source_reading_disagrees: file {raw:g}, snapshot {value.raw_value}' if not equal else
                      'cell re-read from CSV' if unit else 'AI value unchecked: header names no unit')
            if calibrated and equal:
                reason = f'AI calibration unchecked: header unit {unit}, calibrated raw unit {value.raw_unit}'
            rows.append({'id': name, 'colour': colour, 'reason': reason, 'source_digest': digest,
                         'value': raw, 'unit': value.raw_unit if calibrated else unit or value.raw_unit, 'tolerance': max(abs(raw)*1e-3, 1e-12),
                         'asserted_value': value.value})
            value.raw_value, value.raw_unit, value.value = raw, value.raw_unit if calibrated else unit or value.raw_unit, None
            if not calibrated:
                value.conversion_factor = value.conversion_offset = value.conversion_note = None
    return rows


def source_parameters(observed, spec) -> tuple[object, list[dict]]:
    """Use source parameters in the evaluated audit, leaving the caller's audit untouched."""
    result = spec.model_copy(deep=True)
    components = {c.id: c for c in result.system.components}
    rows = []
    for component in result.system.components:
        for key, value in (component.parameters or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or any(
                    token in key for token in ('residual_scale', '_bound', '_initial_guess', '_scale')):
                continue
            name = component.id + '.' + key
            declaration = observed.parameters.get(name, {})
            row, reading = source_row('parameter:' + name, declaration.get('quote'), value,
                                      declaration.get('unit'), observed._sources)
            if reading['kind'] == 'value':
                components[component.id].parameters[key] = reading['value']
            rows.append(row)
    return result, rows
