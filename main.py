import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt

# Variables d'entrée (0 à 100)
duels   = ctrl.Antecedent(np.arange(0, 101, 1), 'duels')
aerien  = ctrl.Antecedent(np.arange(0, 101, 1), 'aerien')
vitesse = ctrl.Antecedent(np.arange(0, 101, 1), 'vitesse')
relance = ctrl.Antecedent(np.arange(0, 101, 1), 'relance')

def definir_niveaux(var):
    var['faible'] = fuzz.trapmf(var.universe, [0, 0, 25, 50])
    var['moyen']  = fuzz.trimf(var.universe,  [25, 50, 75])
    var['fort']   = fuzz.trapmf(var.universe, [50, 75, 100, 100])

for v in (duels, aerien, vitesse, relance):
    definir_niveaux(v)

# Vérification visuelle des chevauchements
duels.view()
plt.show()