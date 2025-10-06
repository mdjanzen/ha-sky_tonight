# Sky Tonight

A Home Assistant custom integration that uses [Skyfield](https://rhodesmill.org/skyfield/) to calculate celestial body events, including rise/set times and azimuths.

## Installation

### Via HACS

1) Open HACS.
2) Click on the three dot menu in the top right corner of the screen → "Custom Repositories"
3) Paste https://github.com/mdjanzen/ha-sky_tonight in the Repositories textbox and select Dashboard in the Type dropdown.
4) Click Add.
5) Search for 'Sky Tonight' and click the three dot menu besides it.
6) Click Download.
7) Finally, refresh your browser window.


### Manual
Copy the `custom_components/sky_tonight` folder into your Home Assistant `config/custom_components/` directory and restart.

## Configuration
The integration provides a config flow that allows selecting multiple celestial bodies to track.
 
## Special Thanks
Thank you to the Sky Tonight Card for inspiration. 