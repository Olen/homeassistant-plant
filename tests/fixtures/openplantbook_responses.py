"""Mock OpenPlantbook API responses for testing."""

# Search result for "monstera"
SEARCH_RESULT_MONSTERA = {
    "monstera deliciosa": "Monstera deliciosa",
    "monstera adansonii": "Monstera adansonii",
    "monstera obliqua": "Monstera obliqua",
}

# Get result for "monstera deliciosa"
GET_RESULT_MONSTERA_DELICIOSA = {
    "pid": "monstera deliciosa",
    "display_pid": "Monstera deliciosa",
    "alias": "Swiss cheese plant",
    "max_light_mmol": 6000,
    "min_light_mmol": 1500,
    "max_light_lux": 35000,
    "min_light_lux": 1500,
    "max_temp": 30,
    "min_temp": 15,
    "max_env_humid": 80,
    "min_env_humid": 50,
    "max_soil_moist": 60,
    "min_soil_moist": 20,
    "max_soil_ec": 2000,
    "min_soil_ec": 350,
    "image_url": "https://opb-img.plantbook.io/monstera_deliciosa.jpg",
}

# Search result for "ficus"
SEARCH_RESULT_FICUS = {
    "ficus lyrata": "Ficus lyrata",
    "ficus elastica": "Ficus elastica",
    "ficus benjamina": "Ficus benjamina",
}

# Get result for "ficus lyrata"
GET_RESULT_FICUS_LYRATA = {
    "pid": "ficus lyrata",
    "display_pid": "Ficus lyrata",
    "alias": "Fiddle-leaf fig",
    "max_light_mmol": 8000,
    "min_light_mmol": 2000,
    "max_light_lux": 50000,
    "min_light_lux": 2500,
    "max_temp": 28,
    "min_temp": 12,
    "max_env_humid": 70,
    "min_env_humid": 40,
    "max_soil_moist": 55,
    "min_soil_moist": 25,
    "max_soil_ec": 1800,
    "min_soil_ec": 400,
    "image_url": "https://opb-img.plantbook.io/ficus_lyrata.jpg",
}

# Empty search result
SEARCH_RESULT_EMPTY = {}

# Result when species not found
GET_RESULT_NOT_FOUND = None
