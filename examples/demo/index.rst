sphinx-contrib-prefect demo
===========================

This project documents the flows in ``demo.flows``. The
``prefect-flow-index`` directive scans ``prefect_modules`` from ``conf.py`` and
renders one section per flow with a main-flow docstring marker, so the three
flows below are discovered without listing them by hand.

.. toctree::
   :maxdepth: 2
   :caption: Pages

   standalone
   variants

Main flows
----------

.. prefect-flow-index::
