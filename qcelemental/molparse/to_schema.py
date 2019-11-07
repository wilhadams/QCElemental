from copy import deepcopy
from typing import Any, Dict, Union

import numpy as np

from ..exceptions import ValidationError
from ..physical_constants import constants
from ..util import unnp
from .to_string import formula_generator


def to_schema(
    molrec: Dict[str, Any], dtype: Union[str, int], units: str = 'Bohr', *, np_out: bool = False, copy: bool = True
) -> Dict[str, Any]:
    """Translate molparse internal Molecule spec into dictionary from other schemas.

    Parameters
    ----------
    molrec : dict
        Psi4 json Molecule spec.
    dtype : {'psi4', 1, 2}
        Molecule schema format.
        ``1`` is https://molssi-qc-schema.readthedocs.io/en/latest/auto_topology.html V1 + #44 + #53
        ``2`` is ``1`` with internal schema_name/version (https://github.com/MolSSI/QCSchema/pull/60)
    units : {'Bohr', 'Angstrom'}
        Units in which to write string. There is not an option to write in
        intrinsic/input units. Some `dtype` may not allow all units.
    np_out : bool, optional
        When `True`, fields originating from geom, elea, elez, elem, mass, real, elbl will be ndarray.
        Use `False` to get a json-able version.
    #return_type : {'json', 'yaml'} Serialization format string to return.

    Returns
    -------
    qcschema : dict
        Dictionary of the `dtype` repr of `molrec`.

    """
    qcschema: Dict = {}

    geom = np.array(molrec["geom"], copy=copy)

    if molrec["units"] == 'Bohr' and units == 'Bohr':
        pass
    elif molrec['units'] == 'Angstrom' and units == 'Bohr' and 'input_units_to_au' in molrec:
        geom = geom * molrec['input_units_to_au']
    else:
        geom = geom * constants.conversion_factor(molrec['units'], units)

    nat = geom.shape[0] // 3

    name = molrec.get('name', formula_generator(molrec['elem']))
    #    tagline = """auto-generated by qcdb from molecule {}""".format(name)

    if dtype == 'psi4':
        if units not in ['Angstrom', 'Bohr']:
            raise ValidationError(
                """Psi4 Schema {} allows only 'Bohr'/'Angstrom' coordinates, not {}.""".format(dtype, units)
            )
        qcschema = deepcopy(molrec)
        qcschema['geom'] = geom
        qcschema['units'] = units
        qcschema['name'] = name

    elif dtype in [1, 2]:
        if units != 'Bohr':
            raise ValidationError("""QC_JSON_Schema {} allows only 'Bohr' coordinates, not {}.""".format(dtype, units))

        molecule: Dict = {}
        molecule["validated"] = True
        molecule['symbols'] = np.array(molrec['elem'], copy=copy)
        molecule['geometry'] = geom
        molecule['masses'] = np.array(molrec['mass'], copy=copy)
        molecule['atomic_numbers'] = np.array(molrec['elez'], copy=copy)
        molecule['mass_numbers'] = np.array(molrec['elea'], copy=copy)
        molecule['atom_labels'] = np.array(molrec['elbl'], copy=copy)
        molecule['name'] = name
        if 'comment' in molrec:
            molecule['comment'] = molrec['comment']
        molecule['molecular_charge'] = molrec['molecular_charge']
        molecule['molecular_multiplicity'] = molrec['molecular_multiplicity']
        molecule['real'] = np.array(molrec['real'], copy=copy)
        fidx = np.split(np.arange(nat), molrec['fragment_separators'])
        molecule['fragments'] = [fr.tolist() for fr in fidx]
        molecule['fragment_charges'] = np.array(molrec['fragment_charges']).tolist()
        molecule['fragment_multiplicities'] = np.array(molrec['fragment_multiplicities']).tolist()
        molecule['fix_com'] = molrec['fix_com']
        molecule['fix_orientation'] = molrec['fix_orientation']
        if 'fix_symmetry' in molrec:
            molecule['fix_symmetry'] = molrec['fix_symmetry']
        molecule['provenance'] = deepcopy(molrec['provenance'])
        if 'connectivity' in molrec:
            molecule['connectivity'] = deepcopy(molrec['connectivity'])

        if dtype == 1:
            qcschema = {'schema_name': 'qcschema_input', 'schema_version': 1, 'molecule': molecule}
        elif dtype == 2:
            qcschema = molecule
            qcschema.update({'schema_name': 'qcschema_molecule', 'schema_version': 2})

    else:
        raise ValidationError(
            "Schema dtype not understood, valid options are {{'psi4', 1, 2}}. Found {}.".format(dtype)
        )

    if not np_out:
        qcschema = unnp(qcschema)

    return qcschema

    # if return_type == 'json':
    #    return json.dumps(qcschema)
    # elif return_type == 'yaml':
    #    import yaml
    #    return yaml.dump(qcschema)
    # else:
    #    raise ValidationError("""Return type ({}) not recognized.""".format(return_type))
