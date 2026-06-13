const SHORT_NAMES = {
  'United States of America': 'USA',
  'United Kingdom of Great Britain and Northern Ireland': 'UK',
  'Russian Federation': 'Russia',
  'Republic of Korea': 'South Korea',
  "Democratic People's Republic of Korea": 'North Korea',
  'Iran (Islamic Republic of)': 'Iran',
  'Syrian Arab Republic': 'Syria',
  'Bolivia (Plurinational State of)': 'Bolivia',
  'Venezuela (Bolivarian Republic of)': 'Venezuela',
  'United Republic of Tanzania': 'Tanzania',
  'Democratic Republic of the Congo': 'DR Congo',
  'Central African Republic': 'CAR',
  'Czech Republic': 'Czechia',
  "Côte d'Ivoire": "Cote d'Ivoire",
  'Timor-Leste': 'East Timor',
  'Brunei Darussalam': 'Brunei',
  'Lao People\'s Democratic Republic': 'Laos',
  'Viet Nam': 'Vietnam',
  'Myanmar': 'Burma',
  'Cabo Verde': 'Cape Verde',
  'Eswatini': 'Eswatini',
  'North Macedonia': 'N. Macedonia',
  'Bosnia and Herzegovina': 'Bosnia',
  'United Kingdom': 'UK',
  'United States': 'USA',
  'High-income countries': 'High Income',
  'Lower-middle-income countries': 'Low-Mid Income',
  'Upper-middle-income countries': 'Up-Mid Income',
  'Low-income countries': 'Low Income',
}

const ISO_TO_NAME = {
  'AFG': 'Afghanistan', 'AGO': 'Angola', 'ALB': 'Albania', 'ARE': 'UAE',
  'ARG': 'Argentina', 'ARM': 'Armenia', 'AUS': 'Australia', 'AUT': 'Austria',
  'AZE': 'Azerbaijan', 'BDI': 'Burundi', 'BEL': 'Belgium', 'BEN': 'Benin',
  'BFA': 'Burkina Faso', 'BGD': 'Bangladesh', 'BGR': 'Bulgaria', 'BHR': 'Bahrain',
  'BHS': 'Bahamas', 'BIH': 'Bosnia', 'BLR': 'Belarus', 'BLZ': 'Belize',
  'BOL': 'Bolivia', 'BRA': 'Brazil', 'BRN': 'Brunei', 'BTN': 'Bhutan',
  'BWA': 'Botswana', 'CAF': 'CAR', 'CAN': 'Canada', 'CHE': 'Switzerland',
  'CHL': 'Chile', 'CHN': 'China', 'CIV': "Cote d'Ivoire", 'CMR': 'Cameroon',
  'COD': 'DR Congo', 'COG': 'Congo', 'COL': 'Colombia', 'COM': 'Comoros',
  'CPV': 'Cape Verde', 'CRI': 'Costa Rica', 'CUB': 'Cuba', 'CYP': 'Cyprus',
  'CZE': 'Czechia', 'DEU': 'Germany', 'DJI': 'Djibouti', 'DNK': 'Denmark',
  'DOM': 'Dominican Republic', 'DZA': 'Algeria', 'ECU': 'Ecuador', 'EGY': 'Egypt',
  'ERI': 'Eritrea', 'ESP': 'Spain', 'EST': 'Estonia', 'ETH': 'Ethiopia',
  'FIN': 'Finland', 'FJI': 'Fiji', 'FRA': 'France', 'GAB': 'Gabon',
  'GBR': 'UK', 'GEO': 'Georgia', 'GHA': 'Ghana', 'GIN': 'Guinea',
  'GMB': 'Gambia', 'GNB': 'Guinea-Bissau', 'GNQ': 'Equatorial Guinea', 'GRC': 'Greece',
  'GTM': 'Guatemala', 'GUY': 'Guyana', 'HND': 'Honduras', 'HRV': 'Croatia',
  'HTI': 'Haiti', 'HUN': 'Hungary', 'IDN': 'Indonesia', 'IND': 'India',
  'IRL': 'Ireland', 'IRN': 'Iran', 'IRQ': 'Iraq', 'ISL': 'Iceland',
  'ISR': 'Israel', 'ITA': 'Italy', 'JAM': 'Jamaica', 'JOR': 'Jordan',
  'JPN': 'Japan', 'KAZ': 'Kazakhstan', 'KEN': 'Kenya', 'KGZ': 'Kyrgyzstan',
  'KHM': 'Cambodia', 'KOR': 'South Korea', 'KWT': 'Kuwait', 'LAO': 'Laos',
  'LBN': 'Lebanon', 'LBR': 'Liberia', 'LBY': 'Libya', 'LKA': 'Sri Lanka',
  'LSO': 'Lesotho', 'LTU': 'Lithuania', 'LUX': 'Luxembourg', 'LVA': 'Latvia',
  'MAR': 'Morocco', 'MDA': 'Moldova', 'MDG': 'Madagascar', 'MDV': 'Maldives',
  'MEX': 'Mexico', 'MKD': 'N. Macedonia', 'MLI': 'Mali', 'MLT': 'Malta',
  'MMR': 'Myanmar', 'MNE': 'Montenegro', 'MNG': 'Mongolia', 'MOZ': 'Mozambique',
  'MRT': 'Mauritania', 'MUS': 'Mauritius', 'MWI': 'Malawi', 'MYS': 'Malaysia',
  'NAM': 'Namibia', 'NER': 'Niger', 'NGA': 'Nigeria', 'NIC': 'Nicaragua',
  'NLD': 'Netherlands', 'NOR': 'Norway', 'NPL': 'Nepal', 'NZL': 'New Zealand',
  'OMN': 'Oman', 'PAK': 'Pakistan', 'PAN': 'Panama', 'PER': 'Peru',
  'PHL': 'Philippines', 'PNG': 'Papua New Guinea', 'POL': 'Poland', 'PRK': 'North Korea',
  'PRT': 'Portugal', 'PRY': 'Paraguay', 'PSE': 'Palestine', 'QAT': 'Qatar',
  'ROU': 'Romania', 'RUS': 'Russia', 'RWA': 'Rwanda', 'SAU': 'Saudi Arabia',
  'SDN': 'Sudan', 'SEN': 'Senegal', 'SGP': 'Singapore', 'SLE': 'Sierra Leone',
  'SLV': 'El Salvador', 'SMR': 'San Marino', 'SOM': 'Somalia', 'SRB': 'Serbia',
  'SSD': 'South Sudan', 'STP': 'Sao Tome', 'SUR': 'Suriname', 'SVK': 'Slovakia',
  'SVN': 'Slovenia', 'SWE': 'Sweden', 'SWZ': 'Eswatini', 'SYR': 'Syria',
  'TCD': 'Chad', 'TGO': 'Togo', 'THA': 'Thailand', 'TJK': 'Tajikistan',
  'TKM': 'Turkmenistan', 'TLS': 'East Timor', 'TON': 'Tonga', 'TTO': 'Trinidad',
  'TUN': 'Tunisia', 'TUR': 'Turkey', 'TWN': 'Taiwan', 'TZA': 'Tanzania',
  'UGA': 'Uganda', 'UKR': 'Ukraine', 'URY': 'Uruguay', 'USA': 'USA',
  'UZB': 'Uzbekistan', 'VNM': 'Vietnam', 'YEM': 'Yemen', 'ZAF': 'South Africa',
  'ZMB': 'Zambia', 'ZWE': 'Zimbabwe',
}

const WHO_REGION_CODES = {
  'AFR': 'Africa', 'AMR': 'Americas', 'EMR': 'E. Mediterranean',
  'EUR': 'Europe', 'SEAR': 'S.E. Asia', 'WPR': 'W. Pacific',
}

const SPECIAL_GROUPS = {
  'UNSDG_LDC': 'Least Developed',
  'UNSDG_L LDC': 'Landlocked LDC',
  'UNSDG_SIDS': 'Small Islands',
}

export function shortName(name) {
  if (!name) return name
  if (SHORT_NAMES[name]) return SHORT_NAMES[name]
  if (ISO_TO_NAME[name]) return ISO_TO_NAME[name]
  if (WHO_REGION_CODES[name]) return WHO_REGION_CODES[name]
  if (SPECIAL_GROUPS[name]) return SPECIAL_GROUPS[name]
  if (name.length > 18) {
    const words = name.split(' ')
    if (words.length > 3) {
      return words.slice(0, 3).join(' ') + '...'
    }
  }
  return name
}

export function isInvalidDisease(name) {
  if (!name) return true
  const lower = name.toLowerCase()
  return lower === 'nan' || lower === 'places_health_measures' || lower === 'null' || lower === 'undefined' || lower === 'malaria'
}

export function isCleanRecord(record) {
  if (!record) return false
  if (isInvalidDisease(record.disease_name)) return false
  if (record.disease_category !== 'Communicable' && record.disease_category !== 'Non-communicable') return false
  const count = Number(record.case_count)
  if (isNaN(count) || count <= 0) return false
  return true
}

export const VALID_DISEASES = ['Hepatitis B', 'Tuberculosis', 'Hepatitis C', 'Influenza', 'Cardiovascular Disease']

export function cleanDiseaseName(name) {
  if (isInvalidDisease(name)) return null
  for (const d of VALID_DISEASES) {
    if (name.toLowerCase().includes(d.toLowerCase())) return d
  }
  return name
}
