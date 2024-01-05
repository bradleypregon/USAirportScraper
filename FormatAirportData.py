import json

file = open('export_bak.json')
data = json.load(file)

airports = []

for line in data:
  formatData = { 
    "coordinates": { 
      "lat": line["coordinates"]["lat"],
      "long": line["coordinates"]["long"]
    },
    "properties": { 
      "airportName": line["properties"]["airportName"],
      "cityServed": line["properties"]["cityServed"],
      "faa": line["properties"]["faa"],
      "iata": line["properties"]["iata"],
      "icao": line["properties"]["icao"],
      "size": line["properties"]["size"],
    }
  }

  airports.append(formatData)

with open("export.json", "w") as outfile:
  json.dump(airports, outfile)
file.close()
