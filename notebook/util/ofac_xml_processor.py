# tool/data_ingestion/ofac_xml_processor.py

import xml.etree.ElementTree as ET
from typing import Dict

import requests

def parse_entity(entity, ns):
    """Parses a single <entity> element into a structured dictionary."""
    return {
        'EntityID': entity.get('id'),
        'GeneralInfo': {
            'IdentityID': entity.findtext(f'./{ns}generalInfo/{ns}identityId', default=''),
            'EntityType': entity.findtext(f'./{ns}generalInfo/{ns}entityType', default=''),
            'EntityTypeRef': entity.find(f'./{ns}generalInfo/{ns}entityType').get('refId') if entity.find(f'./{ns}generalInfo/{ns}entityType') is not None else None,
            'Title': entity.findtext(f'./{ns}generalInfo/{ns}title', default='')
        },
        'Names': [
            {
                'ID': name.get('id'),
                'IsPrimary': name.findtext(f'./{ns}isPrimary', default='false'),
                'IsLowQuality': name.findtext(f'./{ns}isLowQuality', default='false'),
                'AliasType': name.findtext(f'./{ns}aliasType', default=None),
                'Translations': [
                    {
                        'Script': trans.findtext(f'./{ns}script', default=''),
                        'FormattedFirstName': trans.findtext(f'./{ns}formattedFirstName', default=''),
                        'FormattedLastName': trans.findtext(f'./{ns}formattedLastName', default=''),
                        'FormattedFullName': trans.findtext(f'./{ns}formattedFullName', default=''),
                        'NameParts': [
                            {
                                'Type': part.findtext(f'./{ns}type', default=''),
                                'Value': part.findtext(f'./{ns}value', default='')
                            } for part in trans.findall(f'./{ns}nameParts/{ns}namePart')
                        ]
                    } for trans in name.findall(f'./{ns}translations/{ns}translation')
                ]
            } for name in entity.findall(f'./{ns}names/{ns}name')
        ],
        'Addresses': [
            {
                'ID': address.get('id'),
                'Country': address.findtext(f'./{ns}country', default=None),
                'Translations': [
                    {
                        'Script': trans.findtext(f'./{ns}script', default=''),
                        'AddressParts': {
                            part.findtext(f'./{ns}type', default=''): part.findtext(f'./{ns}value', default='')
                            for part in trans.findall(f'./{ns}addressParts/{ns}addressPart')
                        }
                    } for trans in address.findall(f'./{ns}translations/{ns}translation')
                ]
            } for address in entity.findall(f'./{ns}addresses/{ns}address')
        ],
        'Features': {
            feature.findtext(f'./{ns}type', default=''): {
                'Value': feature.findtext(f'./{ns}value', default=''),
                'Details': {
                    'ID': feature.get('id'),
                    'IsPrimary': feature.findtext(f'./{ns}isPrimary', default='false'),
                    'ValueRef': feature.findtext(f'./{ns}valueRefId', default=None)
                }
            } for feature in entity.findall(f'./{ns}features/{ns}feature')
        },
        'Sanctions': {
            'Lists': [
                {
                    'ID': s_list.get('id'),
                    'RefID': s_list.get('refId'),
                    'Value': s_list.text.strip() if s_list.text else None,
                    'DatePublished': s_list.get('datePublished')
                } for s_list in entity.findall(f'./{ns}sanctionsLists/{ns}sanctionsList')
            ],
            'Programs': [
                {
                    'ID': s_program.get('id'),
                    'RefID': s_program.get('refId'),
                    'Value': s_program.text.strip() if s_program.text else None
                } for s_program in entity.findall(f'./{ns}sanctionsPrograms/{ns}sanctionsProgram')
            ],
            'Types': [
                {
                    'ID': s_type.get('id'),
                    'RefID': s_type.get('refId'),
                    'Value': s_type.text.strip() if s_type.text else None
                } for s_type in entity.findall(f'./{ns}sanctionsTypes/{ns}sanctionsType')
            ]
        },
        'IdentityDocuments': [
            {
                'ID': doc.get('id'),
                'Type': doc.findtext(f'./{ns}type', default=''),
                'Name': doc.findtext(f'./{ns}name', default=''),
                'DocumentNumber': doc.findtext(f'./{ns}documentNumber', default=''),
                'IsValid': doc.findtext(f'./{ns}isValid', default='false'),
                'IssuingLocation': doc.findtext(f'./{ns}issuingLocation', default=''),
                'IssuingCountry': doc.findtext(f'./{ns}issuingCountry', default='')
            } for doc in entity.findall(f'./{ns}identityDocuments/{ns}identityDocument')
        ]
    }

def convert_xml_to_json(input_xml):
    """Converts OFAC XML data to JSON while retaining structure."""
    print("Converting XML to JSON")
    ns = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML}"
    root = ET.fromstring(input_xml)
    
    entities = root.find(f'{ns}entities')
    if entities is None:
        raise ValueError("No <entities> section found in XML.")
    
    data = {
        "total_records": len(entities),
        "individuals": [],
        "entities": [],
        "summary": {  # ✅ Add summary section
            "entity_types": {},
            "country_breakdown": {},
            "program_breakdown": {}
        }
    }
    
    entity_type_counts = {}
    country_counts = {}
    program_counts = {}

    for entity in entities.findall(f'{ns}entity'):
        entity_data = parse_entity(entity, ns)
        
        # Categorize as Individual or Entity
        if entity_data['GeneralInfo']['EntityType'] == 'Individual':
            data['individuals'].append(entity_data)
        else:
            data['entities'].append(entity_data)

        # ✅ Collect entity type counts
        entity_type = entity_data['GeneralInfo']['EntityType']
        entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

        # ✅ Collect country counts
        for address in entity_data.get('Addresses', []):
            country = address.get('Country')
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

        # ✅ Collect sanction program counts
        for program in entity_data.get('Sanctions', {}).get('Programs', []):
            program_name = program.get('Value')
            if program_name:
                program_counts[program_name] = program_counts.get(program_name, 0) + 1

    # ✅ Add computed summary statistics
    data['summary']['entity_types'] = entity_type_counts
    data['summary']['country_breakdown'] = country_counts
    data['summary']['program_breakdown'] = program_counts

    return data  # ✅ Now includes 'summary'

# Example usage
# convert_xml_to_json("ofac_xml_small.xml", "ofac_data_small.json")
def fetch_and_process_ofac_data() -> Dict:
    """Fetches and processes the OFAC XML data."""
    try:
        # Fetch XML from URL
        print("Fetching OFAC XML data")
        xml_url = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ENHANCED.XML"
        xml_response = requests.get(xml_url)
        xml_response.raise_for_status()

        # Convert XML to JSON
        return convert_xml_to_json(xml_response.content)

    except Exception as e:
        raise Exception(f"Error processing OFAC data: {str(e)}")