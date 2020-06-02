import os
import sdg
from sdg.outputs import OutputBase
from sdg.data import write_csv
from sdg.json import write_json, df_to_list_dict

class OutputOpenSdg(OutputBase):
    """Output SDG data/metadata in the formats expected by Open SDG."""


    def __init__(self, inputs, schema, output_folder='_site', translations=None,
        reporting_status_extra_fields=None):
        """Constructor for OutputOpenSdg.

        Parameters
        ----------

        Inherits all the parameters from OutputBase, plus the following:

        reporting_status_extra_fields : string
            To be passed as "extra_fields" to sdg.stats.reporting_status.


        """
        if translations is None:
            translations = []

        OutputBase.__init__(self, inputs, schema, output_folder, translations)
        self.reporting_status_grouping_fields = reporting_status_extra_fields


    def build(self, language=None):
        """Write the JSON output expected by Open SDG. Overrides parent."""
        status = True
        all_meta = dict()
        all_headline = dict()
        site_dir = self.output_folder

        # Write the schema.
        schema_output = sdg.schemas.SchemaOutputOpenSdg(schema=self.schema)
        schema_output_folder = os.path.join(site_dir, 'meta')
        schema_output.write_schema(output_folder=schema_output_folder, filename='schema.json')

        # Write the translations.
        translation_output = sdg.translations.TranslationOutputJson(self.translations)
        translation_folder = os.path.join(site_dir, 'translations')
        translation_output.write_translations(
            language=language,
            output_folder=translation_folder,
            filename='translations.json'
        )

        for indicator_id in self.get_indicator_ids():
            indicator = self.get_indicator_by_id(indicator_id).language(language)
            # Output all the csvs
            status = status & write_csv(indicator_id, indicator.data, ftype='data', site_dir=site_dir)
            status = status & write_csv(indicator_id, indicator.edges, ftype='edges', site_dir=site_dir)
            status = status & write_csv(indicator_id, indicator.headline, ftype='headline', site_dir=site_dir)
            # And JSON
            data_dict = df_to_list_dict(indicator.data, orient='list')
            edges_dict = df_to_list_dict(indicator.edges, orient='list')
            headline_dict = df_to_list_dict(indicator.headline, orient='records')

            status = status & write_json(indicator_id, data_dict, ftype='data', gz=False, site_dir=site_dir)
            status = status & write_json(indicator_id, edges_dict, ftype='edges', gz=False, site_dir=site_dir)
            status = status & write_json(indicator_id, headline_dict, ftype='headline', gz=False, site_dir=site_dir)

            # combined
            comb = {'data': data_dict, 'edges': edges_dict}
            status = status & write_json(indicator_id, comb, ftype='comb', gz=False, site_dir=site_dir)

            # Metadata
            status = status & sdg.json.write_json(indicator_id, indicator.meta, ftype='meta', site_dir=site_dir)

            # Append to the build-time "all" output
            all_meta[indicator_id] = indicator.meta
            all_headline[indicator_id] = headline_dict

        status = status & sdg.json.write_json('all', all_meta, ftype='meta', site_dir=site_dir)
        status = status & sdg.json.write_json('all', all_headline, ftype='headline', site_dir=site_dir)

        stats_reporting = sdg.stats.reporting_status(self.schema, all_meta, self.reporting_status_grouping_fields)
        status = status & sdg.json.write_json('reporting', stats_reporting, ftype='stats', site_dir=site_dir)

        indicator_export_service = sdg.IndicatorExportService(site_dir, self.indicators)
        indicator_export_service.export_all_indicator_data_as_zip_archive()

        return(status)


    def generate_sort_order(self, indicator):
        """Generate a sortable string from an indicator id.

        Parameters
        ----------
        indicator : Indicator
            An instance of the Indicator class.

        Returns
        -------
        string
            A string suitable for sorting indicators.
        """
        parts = indicator.get_indicator_id().split('.')
        sorted = []
        for part in parts:
            padded_part = part if len(part) > 1 else '0' + part
            sorted.append(padded_part)
        return '-'.join(sorted)


    def minimum_metadata(self, indicator):
        """Provide minimum metadata for an indicator. Overrides parent."""
        minimum = {
            'indicator': indicator.get_indicator_id(),
            'target_id': indicator.get_target_id(),
            'sdg_goal': indicator.get_goal_id(),
            'reporting_status': 'complete' if (indicator.has_data() or indicator.is_statistical() == False) else 'notstarted',
            'data_non_statistical': False if indicator.has_data() else True,
            'graph_type': 'line',
            'indicator_sort_order': self.generate_sort_order(indicator)
        }

        # Add names only if the indicator has one.
        if indicator.has_name():
            minimum['indicator_name'] = indicator.get_name()
            minimum['graph_title'] = indicator.get_name()

        return minimum


    def get_documentation_title(self):
        return 'Open SDG output'


    def get_documentation_content(self, languages=None):
        if languages is None:
            languages = ['']

        indicator_ids = list(self.get_indicator_ids())[:2]

        sections = [
            {
                'title': 'Headlines',
                'description': 'CSV/JSON files containing "headline" (aggregated only) data for indicators',
                'endpoints': [
                    '{language}/headline/{indicator_id}.csv',
                    '{language}/headline/{indicator_id}.json'
                ]
            },
            {
                'title': 'Data',
                'description': 'CSV/JSON files containing fully disaggregated data for indicators',
                'endpoints': [
                    '{language}/data/{indicator_id}.csv',
                    '{language}/data/{indicator_id}.json'
                ]
            },
            {
                'title': 'Edges',
                'description': 'CSV/JSON files containing "edges" (relationships between disaggregations) data for indicators',
                'endpoints': [
                    '{language}/edges/{indicator_id}.csv',
                    '{language}/edges/{indicator_id}.json'
                ]
            },
            {
                'title': 'Combined edges and data',
                'description': 'JSON files containing both the fully-disaggregated and "edges" data mentioned above',
                'endpoints': [
                    '{language}/comb/{indicator_id}.json'
                ]
            },
            {
                'title': 'Metadata',
                'description': 'JSON files containing metadata for the indicators',
                'endpoints': [
                    '{language}/comb/{indicator_id}.json'
                ]
            },
            {
                'title': 'Zip file of CSV data',
                'description': 'Zip files containing all indicators in CSV form',
                'endpoints': [
                    '{language}/zip/all_indicators.zip'
                ]
            },
            {
                'title': 'Zip file information',
                'description': 'JSON file containing information about the above-mentioned zip files',
                'endpoints': [
                    '{language}/zip/all_indicators.json'
                ]
            },
            {
                'title': 'Reporting status',
                'description': 'JSON file containing information about the reporting status of the indicators',
                'endpoints': [
                    '{language}/stats/reporting.json'
                ]
            },
            {
                'title': 'Translations',
                'description': 'JSON file containing all the translations used in the platform',
                'endpoints': [
                    '{language}/translations/translations.json'
                ]
            }
        ]

        output = '<p>This output includes a variety of endpoints. Examples are below:<p>'
        for section in sections:
            output += '<h2>' + section['title'] + '</h2>'
            output += '<p>' + section['description'] + '</p>'
            output += '<ul>'
            for language in languages:
                for indicator_id in indicator_ids:
                    for endpoint in section['endpoints']:
                        path = endpoint.format(language=language, indicator_id=indicator_id)
                        output += '<li><a href="' + path + '">' + path + '</a></li>'
            output += '<li>etc...</li>'
            output += '</ul>'

        return output
