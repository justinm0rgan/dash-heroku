# NYC Tree Health

This app takes data from [NYC Open Data - 2015 Street Tree Census](https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh) and displays:

- Tree `health` by Borough
- Tree `health` by Borough by `steward` type

It is filtered by borough through a geospatial choropleth map aggregated by tree count.    
Tree species can be chosen via drop-down.

Results are depicted in simple bar and grouped bar charts, with the purpose being to elucidate if the increased presence of `stewards` aids in increased tree `health` per borough.

This app can be viewed live on Heroku infrastructure at [https://nyc-tree-health.herokuapp.com/](https://nyc-tree-health.herokuapp.com/)
