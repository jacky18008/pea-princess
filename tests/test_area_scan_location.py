"""Geographic research must start from a resolved named street, not a guessed point."""
import json
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / 'skills/vet-flat/scripts'
sys.path.insert(0, str(SCRIPTS))
import area_scan as scan
import geo


class OutcodeLookupTests(unittest.TestCase):
    def response(self, value):
        return {'body': json.dumps(value), 'ok': True, 'status': 200, 'note': '', 'retrieved_at': '2026-09-12'}

    def test_uses_separate_endpoint_and_retains_coarse_provenance(self):
        with patch.object(geo, 'fetch', return_value=self.response({'status': 200, 'result':
                {'outcode': 'N6', 'latitude': 51.57, 'longitude': -0.14}})) as fetch:
            result = geo.lookup_outcode(' n6 ')
        self.assertEqual('https://api.postcodes.io/outcodes/N6', fetch.call_args[0][0])
        self.assertTrue(result['ok'])
        self.assertEqual('postal_district', result['precision'])
        self.assertIn('not a home', result['method'])

    def test_malformed_coordinates_or_wrong_outcode_fail_closed(self):
        for row in ({'outcode': 'N6', 'latitude': None, 'longitude': -0.14},
                    {'outcode': 'N6', 'latitude': float('nan'), 'longitude': -0.14},
                    {'outcode': 'N6', 'latitude': True, 'longitude': -0.14},
                    {'outcode': 'N7', 'latitude': 51.57, 'longitude': -0.14}):
            with self.subTest(row=row), patch.object(geo, 'fetch', return_value=self.response({'status': 200, 'result': row})):
                self.assertFalse(geo.lookup_outcode('N6')['ok'])
        for value in ([], None, {'status': 404, 'error': 'not found'}):
            with patch.object(geo, 'fetch', return_value=self.response(value)):
                self.assertFalse(geo.lookup_outcode('N6')['ok'])

    def test_bad_input_cannot_become_a_path_or_network_request(self):
        with patch.object(geo, 'fetch') as fetch:
            with self.assertRaises(ValueError):
                geo.lookup_outcode('N6/../../anything')
        fetch.assert_not_called()


class StreetLocationTests(unittest.TestCase):
    def ways(self, disconnected=False):
        ways = [{'type': 'way', 'id': 1, 'tags': {'name': 'Example Road', 'highway': 'residential'},
                 'geometry': [{'lat': 51.5, 'lon': -0.13}, {'lat': 51.5, 'lon': -0.125}]}]
        if disconnected:
            ways.append({'type': 'way', 'id': 2, 'tags': ways[0]['tags'],
                         'geometry': [{'lat': 51.51, 'lon': -0.13}, {'lat': 51.51, 'lon': -0.125}]})
        return ways

    def test_representative_midpoint_is_not_seed_dependent(self):
        runner = lambda *a, **k: ({'elements': self.ways()}, {'source_url': 'https://example.invalid/map'})
        a = scan.find_street(51.49, -0.14, 'Example Road', runner=runner, representative=True)
        b = scan.find_street(51.51, -0.12, 'Example Road', runner=runner, representative=True)
        self.assertEqual(a['anchor'], b['anchor'])
        self.assertEqual(a['points'], b['points'])
        self.assertEqual({'lat': 51.5, 'lng': -0.1275}, a['anchor'])
        self.assertEqual('mapped_street_midpoint', a['anchor_method'])

    def test_disconnected_street_does_not_silently_pick_one_component(self):
        runner = lambda *a, **k: ({'elements': self.ways(True)}, {})
        result = scan.find_street(51.5, -0.13, 'Example Road', runner=runner, representative=True)
        self.assertFalse(result['ok'])
        self.assertIn('more precise', result['note'])

    def test_case_variants_cannot_hide_disconnected_sections(self):
        ways = self.ways(True)
        ways[1]['tags'] = dict(ways[1]['tags'], name='example road')
        result = scan.find_street(51.5, -0.13, 'Example Road',
            runner=lambda *a, **k: ({'elements': ways}, {}), representative=True)
        self.assertFalse(result['ok'])

    def test_interior_branch_is_connected_but_not_entirely_sampled(self):
        ways = self.ways()
        ways[0]['geometry'].insert(1, {'lat': 51.5, 'lon': -0.1275})
        ways.append({'type': 'way', 'id': 3, 'tags': dict(ways[0]['tags']),
                     'geometry': [{'lat': 51.5, 'lon': -0.1275}, {'lat': 51.501, 'lon': -0.1275}]})
        def resolve(values):
            return scan.find_street(51.5, -0.13, 'Example Road',
                runner=lambda *a, **k: ({'elements': values}, {}), representative=True)
        a = resolve(ways)
        self.assertTrue(a['ok'])
        self.assertEqual('longest_connected_chain_midpoint', a['anchor_method'])
        self.assertEqual(2, a['location_coverage']['joined_chains'])
        self.assertGreater(a['location_coverage']['mapped_total_length_m'], a['location_coverage']['sample_route_length_m'])
        ways.reverse()
        for way in ways:
            way['geometry'].reverse()
        b = resolve(ways)
        self.assertEqual(a['anchor'], b['anchor'])
        self.assertEqual(a['points'], b['points'])

    def test_full_way_geometry_cannot_move_midpoint_beyond_search(self):
        ways = self.ways()
        ways[0]['geometry'][1]['lon'] = 0.07
        result = scan.find_street(51.5, -0.13, 'Example Road',
            runner=lambda *a, **k: ({'elements': ways}, {}), representative=True)
        self.assertFalse(result['ok'])
        self.assertIn('outside the search radius', result['note'])

    def test_import_api_rejects_unsourced_unpaired_and_invalid_coordinates(self):
        for kwargs in ({'lat': 51.5, 'lng': -0.13}, {'lat': 51.5},
                       {'lat': True, 'lng': -0.13, 'location_source': 'fixture'},
                       {'lat': float('nan'), 'lng': -0.13, 'location_source': 'fixture'},
                       {'lat': 91, 'lng': -0.13, 'location_source': 'fixture'}):
            with self.subTest(kwargs=kwargs), patch.object(scan, '_parallel') as registers, \
                    patch.object(scan, 'find_street') as find:
                with self.assertRaises(ValueError):
                    scan.scan(**kwargs)
                registers.assert_not_called()
                find.assert_not_called()

    def test_successful_outcode_scan_wires_resolved_points_and_provenance(self):
        street = {'ok': True, 'name': 'Example Road', 'anchor': {'lat': 51.51, 'lng': -0.125},
                  'points': [{'lat': 51.51, 'lng': -0.125}, {'lat': 51.511, 'lng': -0.125}],
                  'anchor_method': 'mapped_street_midpoint', 'source_url': 'https://example.invalid/osm',
                  'retrieved_at': '2026-09-12', 'query': 'retained query'}
        def run(jobs):
            for key in ('crime', 'planning', 'roads'):
                self.assertEqual((51.51, -0.125), jobs[key][1][:2])
            self.assertEqual(([(51.51, -0.125), (51.511, -0.125)],), jobs['noise'][1])
            self.assertNotIn('living', jobs)
            return {key: (None, 'offline fixture') for key in jobs}
        with patch.object(geo, 'lookup_outcode', return_value={'ok': True, 'lat': 51.5, 'lng': -0.13,
                    'source_url': 'https://example.invalid/outcodes', 'retrieved_at': '2026-09-12'}), \
                patch.object(scan, 'find_street', return_value=street), patch.object(scan, '_parallel', side_effect=run):
            result = scan.scan(postcode='N6', street='Example Road')
        self.assertEqual('postal_district', result['where']['location_source']['precision'])
        self.assertEqual('retained query', result['where']['street_location']['query'])
        self.assertFalse(result['where']['street_location']['property_location_known'])

    def test_failed_named_street_stops_before_register_queries(self):
        with patch.object(geo, 'lookup_outcode', return_value={'ok': True, 'lat': 51.5, 'lng': -0.13}), \
                patch.object(scan, 'find_street', return_value={'ok': False, 'note': 'missing'}) as find, \
                patch.object(scan, '_parallel') as registers:
            result = scan.scan(postcode='N6', street='Example Road, District, N6')
        self.assertFalse(result['ok'])
        registers.assert_not_called()
        self.assertEqual('Example Road', find.call_args[0][2])
        self.assertTrue(find.call_args[1]['representative'])

    def test_full_postcode_cannot_fall_back_to_an_unmatched_street(self):
        with patch.object(geo, 'lookup', return_value={'ok': True, 'lat': 51.5, 'lng': -0.13}), \
                patch.object(scan, 'find_street', return_value={'ok': False, 'note': 'missing'}), \
                patch.object(scan, '_parallel') as registers:
            self.assertFalse(scan.scan(postcode='N6 1AA', street='Missing Road')['ok'])
        registers.assert_not_called()

    def test_coarse_centroid_without_street_is_not_researched(self):
        with patch.object(geo, 'lookup_outcode') as lookup:
            with self.assertRaises(ValueError):
                scan.scan(postcode='N6')
        lookup.assert_not_called()

    def test_cli_rejects_unsourced_coordinates_before_any_fetch(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'area_scan.py'), '--lat', '51.5', '--lng', '-0.13', '--no-save'], capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertIn('--location-source', result.stderr)
        self.assertNotIn('Milton Park', result.stderr)
