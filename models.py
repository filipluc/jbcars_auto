from dataclasses import dataclass, field


@dataclass
class CarData:
    var_title: str = ""
    var_categorie: str = "Auto's"
    var_brand: str = ""
    var_model: str = ""
    var_desc: str = ""
    var_price: str = ""
    var_picspath: str = ""        # absolute local path to downloaded photos folder
    var_carroserie: str = ""
    var_month: str = ""
    var_year: str = ""
    var_gas: str = ""
    var_transmissie: str = ""
    var_km: str = ""
    var_doors: str = ""
    var_pk: str = ""
    var_cilinder: str = ""
    var_co2: str = ""
    var_euro: str = ""
    var_options: str = ""         # comma-separated raw form values from scraped checkboxes
    var_carcolor: str = ""
    var_interiorcolor: str = ""
    var_pricetype: str = ""       # singleSelectAttribute[priceType] e.g. "Vraagprijs"
    var_upholstery: str = ""      # singleSelectAttribute[upholstery] e.g. "Stof"
    var_drivetrain: str = ""      # singleSelectAttribute[driveTrain] e.g. "Voorwielaandrijving"
    var_seats: str = ""           # numericAttribute[numberOfSeatsBE]
    var_carpass: str = ""         # textAttribute[carPassUrl]
    var_warranty: str = ""        # singleSelectAttribute[warranty]
    var_emptyweight: str = ""     # numericAttribute[emptyWeightCars]
    var_numcylinders: str = ""    # numericAttribute[numberOfCylinders]
    var_towingbraked: str = ""    # numericAttribute[towingWeightBrakes]
    var_towingunbraked: str = ""  # numericAttribute[towingWeightNoBrakes]
    edit_url: str = ""            # URL of original listing edit page (used for deletion)

    def __str__(self):
        return self.var_title
