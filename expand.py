''' Utility class for deduplicating OpenAddresses data.
'''
import json, hashlib, math, sys

# Living on borrowed data.
tokens = [
    ["10th","Tenth"],["11th","Eleventh"],["12th","Twelfth"],["13th","Thirteenth"],
    ["14th","Fourteenth"],["15th","Fifteenth"],["16th","Sixteenth"],["17th","Seventeenth"],
    ["18th","Eighteenth"],["19th","Nineteenth"],["1st","First"],["20th","Twentieth"],
    ["2nd","Second"],["3rd","Third"],["4th","Fourth"],["5th","Fifth"],["6th","Sixth"],
    ["7th","Seventh"],["8th","Eighth"],["9th","Ninth"],["Accs","Access"],["Alwy","Alleyway"],
    ["Aly","Ally","Alley"],["Ambl","Amble"],["App","Approach"],["Apt","Apartment"],
    ["Apts","Apartments"],["Arc","Arcade"],["Artl","Arterial"],["Arty","Artery"],
    ["Ave","Avenue","Av"],["Ba","Banan"],["Bch","Beach"],["Bg","Burg"],["Bgs","Burgs"],
    ["Blf","Bluff"],["Blk","Block"],["Br","Brace","Branch"],["Brg","Bridge"],
    ["Brk","Break","Brook"],["Brks","Brooks"],["Btm","Bottom"],["Bvd","Blvd","Boulevard"],
    ["Bwlk","Boardwalk"],["Byp","Bypa","Bypass"],["Byu","Bayou"],["Bywy","Byway"],
    ["Bzr","Bazaar"],["Cantt","Cantonment"],["Cct","Circuit"],["Ch","Chase","Church"],
    ["Chk","Chowk"],["Cir","Circle"],["Cirs","Circles"],["Cl","Close","Clinic"],
    ["Clb","Club"],["Clf","Cliff"],["Clfs","Cliffs"],["Cll","Calle"],["Cly","Colony"],
    ["Cmn","Common"],["Cnl","Canal"],["Cnr","Cor","Corner"],["Coll","College"],
    ["Con","Concourse"],["Const","Constituency"],["Corpn","Corporation"],["Cp","Camp"],
    ["Cpe","Cape"],["Cplx","Complex"],["Cps","Copse"],["Crcs","Circus"],["Crk","Creek"],
    ["Crse","Course"],["Crst","Crest"],["Csac","Cul-de-sac"],["Cswy","Causeway"],
    ["Ct","Court"],["Ctr","Center","Centre"],["Ctrs","Centers"],["Cts","Courts"],
    ["Ctyd","Courtyard"],["Curv","Curve"],["Cutt","Cutting"],["Cv","Cove"],["Cyn","Canyon"],
    ["Dl","Dale"],["Dm","Dam"],["Dr","Drive"],["Drs","Drives"],["Dt","District"],
    ["Dv","Divide"],["Dvwy","Driveway"],["E","East"],["Elb","Elbow"],["Ent","Entrance"],
    ["Esp","Esplanade"],["Est","Estate"],["Ests","Estates"],["Exp","Expy","Expressway"],
    ["Ext","Extension"],["Exts","Extensions"],["Fawy","Fairway"],["Fld","Field"],
    ["Flds","Fields"],["Fls","Falls"],["Flt","Flat"],["Flts","Flats"],["Folw","Follow"],
    ["Form","Formation"],["Frd","Ford"],["Frg","Forge"],["Frgs","Forges"],["Frk","Fork"],
    ["Frst","Forest"],["Frtg","Frontage"],["Fry","Ferry"],["Ft","Feet","Fort"],
    ["Ftwy","Footway"],["Fwy","Freeway"],["Gdns","Gardens"],["Gen","General"],["Gl","Galli"],
    ["Glde","Glade"],["Govt","Government"],["Gr","Grove"],["Gra","Grange"],["Grd","Grade"],
    ["Grn","Green"],["Gte","Gate"],["Hbr","Harbor"],["Hbrs","Harbors"],["Hird","Highroad"],
    ["Hl","Hill"],["Hls","Hills"],["Holw","Hollow"],["Hosp","Hospital"],["Htl","Hotel"],
    ["Hts","Heights"],["Hvn","Haven"],["Hwy","Highway"],["I","Interstate"],
    ["Ind","Industrial"],["Intg","Interchange"],["Is","Island"],["Iss","Islands"],
    ["Jcts","Junctions"],["Jn","Jct","Jnc","Junction"],["Jr","Junior"],["Knl","Knoll"],
    ["Knls","Knolls"],["Ky","Key"],["Kys","Keys"],["Lck","Lock"],["Lcks","Locks"],
    ["Ldg","Lodge"],["Lf","Loaf"],["Lgt","Light"],["Lgts","Lights"],["Lk","Lake"],
    ["Lks","Lakes"],["Lkt","Lookout"],["Ln","Lane"],["Lndg","Landing"],["Lnwy","Laneway"],
    ["Lt","Lieutenant"],["Lyt","Layout"],["Maj","Major"],["Mal","Mall"],
    ["Mcplty","Municpality"],["Mdw","Meadow"],["Mdws","Meadows"],["Mg","Marg"],
    ["Mhd","Moorhead"],["Mkt","Market"],["Ml","Mill"],["Mndr","Meander"],["Mnr","Manor"],
    ["Mnrs","Manors"],["Mq","Mosque"],["Msn","Mission"],["Mt","Mount"],["Mtn","Mountain"],
    ["Mtwy","Motorway"],["N","North"],["Nck","Neck"],["NE","Northeast"],["Ngr","Nagar"],
    ["Nl","Nalla"],["NW","Northwest"],["Off","Office"],["Orch","Orchard"],["Otlk","Outlook"],
    ["Ovps","Overpass"],["Pchyt","Panchayat"],["Pde","Parade"],["Pf","Platform"],
    ["Ph","Phase"],["Piaz","Piazza"],["Pk","Peak"],["Pkt","Pocket"],["Pl","Place"],
    ["Pln","Plain"],["Plns","Plains"],["Plz","Plza","Plaza"],["Pr","Prairie"],
    ["Prom","Promenade"],["Prt","Port"],["Prts","Ports"],["Psge","Passage"],
    ["Pt","Pnt","Point"],["Pts","Points"],["Pvt","Private"],["Pway","Pathway"],
    ["Pwy","Pkwy","Parkway"],["Qdrt","Quadrant"],["Qtrs","Quarters"],["Qys","Quays"],
    ["R","Riv","River"],["Radl","Radial"],["Rd","Road"],["Rdg","Rdge","Ridge"],
    ["Rdgs","Ridges"],["Rds","Roads"],["Rly","Railway"],["Rmbl","Ramble"],["Rnch","Ranch"],
    ["Rpd","Rapid"],["Rpds","Rapids"],["Rst","Rest"],["Rt","Restaurant"],["Rte","Route"],
    ["Rtt","Retreat"],["Rty","Rotary"],["S","South"],["Sbwy","Subway"],["Sch","School"],
    ["SE","Southeast"],["Sgt","Sergeant"],["Shl","Shoal"],["Shls","Shoals"],["Shr","Shore"],
    ["Shrs","Shores"],["Shun","Shunt"],["Skwy","Skyway"],["Smt","Summit"],["Spg","Spring"],
    ["Spgs","Springs"],["Sq","Square"],["Sqs","Squares"],["Sr","Senior"],
    ["St","Saint","Street"],["Sta","Stn","Station"],["Std","Stadium"],["Stg","Stage"],
    ["Strm","Stream"],["Sts","Streets"],["Svwy","Serviceway"],["SW","Southwest"],
    ["Tce","Ter","Terrace"],["Tfwy","Trafficway"],["Thfr","Thoroughfare"],["Thwy","Thruway"],
    ["Tlwy","Tollway"],["Tpke","Turnpike"],["Tpl","Temple"],["Trce","Trace"],["Trk","Track"],
    ["Trl","Trail","Tr"],["Tunl","Tunnel"],["Twn","Town"],["Un","Union"],["Univ","University"],
    ["Unp","Upas","Underpass"],["Uns","Unions"],["Via","Viad","Viaduct"],["Vis","Vsta","Vista"],
    ["Vl","Ville"],["Vlg","Vill","Village"],["Vlgs","Villages"],["Vly","Valley"],
    ["Vlys","Valleys"],["Vw","View"],["Vws","Views"],["W","West"],["Whrf","Wharf"],
    ["Wkwy","Walkway"],["X","Cr","Cres","Crss","Cross","Crescent"],["Xing","Crossing"],
    ["Wy","Way"],
    ]

# Prepare a map from common street name tokens to opaque hashed values.
token_map = dict()

for token in tokens:
    normal = ', '.join(sorted(token)).encode('utf8')
    value = hashlib.sha1(normal).hexdigest()[:5]
    token_map.update({opt.lower(): value for opt in token})

class Address:
    ''' A single OA address.
    '''
    def __init__(self, source, hash, lon, lat, x, y, number, street, unit, city, district, region, postcode):
        street_normal = ''.join([token_map.get(s, s) for s in street.lower().split()])
        self.source = source
        self.hash = hash
        self.lon = lon
        self.lat = lat
        self.x = x
        self.y = y

        self.number = number
        self.street = street
        self.street_normal = street_normal
        self.unit = unit
        self.city = city
        self.district = district
        self.region = region
        self.postcode = postcode
    
    def quadtiles(self, zoom):
        ''' Return four possible quadtile coordinates for comparison purposes.
        
            Assume x and y are given in Mercator meters.
        '''
        factor, circumference = math.pow(2, zoom), (6378137 * 2 * math.pi)
        row0, col0 = (.5 - self.y / circumference), (.5 + self.x / circumference)
        row, col = int(row0 * factor), int(col0 * factor)
        
        return (
            '{z:.0f}/{x:.0f}/{y:.0f}'.format(y=row + 0, x=col + 0, z=zoom),
            '{z:.0f}/{x:.0f}/{y:.0f}'.format(y=row + 0, x=col + 1, z=zoom),
            '{z:.0f}/{x:.0f}/{y:.0f}'.format(y=row + 1, x=col + 0, z=zoom),
            '{z:.0f}/{x:.0f}/{y:.0f}'.format(y=row + 1, x=col + 1, z=zoom),
            )
    
    def matches(self, other):
        ''' Return true if this address matches another.
        
            Compare on street number, token-normalized street name, and unit.
        '''
        return bool(
            self.number == other.number
            and self.street_normal == other.street_normal
            and self.unit == other.unit
            )
    
    def tojson(self):
        ''' Output a JSON array that can be passed directly to constructor.
        '''
        return json.dumps([
            self.source, self.hash, self.lon, self.lat, self.x, self.y,
            self.number, self.street, self.unit, self.city, self.district,
            self.region, self.postcode
            ])
    
    def __str__(self):
        return self.number + ' ' + self.street + ', ' + self.unit

if __name__ == '__main__':
    import doctest
    doctest.testmod()
