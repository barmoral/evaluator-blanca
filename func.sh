function convert_ff_to_v3 () {
    FF="forcefields/v3/$1"
    cp forcefields/$1 $FF
    sed -i 's/    <vdW version="0.4" potential="Lennard-Jones-12-6" combining_rules="Lorentz-Berthelot" scale12="0.0" scale13="0.0" scale14="0.5" scale15="1.0" cutoff="9.0 \* angstrom \*\* 1" switch_width="1.0 \* angstrom \*\* 1" periodic_method="cutoff" nonperiodic_method="no-cutoff">/    <vdW version="0.3" potential="Lennard-Jones-12-6" combining_rules="Lorentz-Berthelot" scale12="0.0" scale13="0.0" scale14="0.5" scale15="1.0" cutoff="9.0 \* angstrom" switch_width="1.0 \* angstrom" method="cutoff">/g' $FF
    sed -i 's/    <Electrostatics version="0.4" scale12="0.0" scale13="0.0" scale14="0.8333333333" scale15="1.0" cutoff="9.0 \* angstrom \*\* 1" switch_width="0.0 \* angstrom \*\* 1" periodic_potential="Ewald3D-ConductingBoundary" nonperiodic_potential="Coulomb" exception_potential="Coulomb">/    <Electrostatics version="0.3" scale12="0.0" scale13="0.0" scale14="0.8333333333" scale15="1.0" cutoff="9.0 \* angstrom" switch_width="0.0 \* angstrom" method="PME">/g' $FF
    echo "converted $FF"
}