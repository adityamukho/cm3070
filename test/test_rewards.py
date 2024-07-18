import os
import pickle
import sys

import numpy as np
import tmrl.config.config_constants as cfg

if not os.path.exists(cfg.REWARD_PATH):
    print("Reward path does not exist", file=sys.stderr)
    sys.exit(1)
else:
    with open(cfg.REWARD_PATH, 'rb') as f:
        data = pickle.load(f)

        assert data is not None
        assert type(data) is np.ndarray
