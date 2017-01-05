.. . Kicking page rebuild 2014-10-30 17:00:08
.. include:: defs.hrst

.. index:: Contract
.. _Contract:

Contract
========

Schema
------

:id:
    uid, auto-generated

    |ocdsDescription|
    The identifier for this contract.

:awardID:
    string, required

    |ocdsDescription|
    The `Award.id` against which this contract is being issued.

:contractID:
    string, auto-generated, read-only

:title:
    string, required

    |ocdsDescription|
    Contract title

:description:
    string

    |ocdsDescription|
    Contract description

:items:
    List of :ref:`Item` objects, auto-generated, read-only

    |ocdsDescription|
    The goods, services, and any intangible outcomes in this contract. Note: If the items are the same as the award do not repeat.

:suppliers:
    List of :ref:`Organization` objects, auto-generated, read-only

:status:
    string, required

    |ocdsDescription|
    The current status of the contract.

    Possible values are:

    * `pending` - this contract has been proposed, but is not yet in force.
      It may be awaiting signature.
    * `active` - this contract has been signed by all the parties, and is
      now legally in force.
    * `cancelled` - this contract has been cancelled prior to being signed.
    * `terminated` - this contract was signed and in force, and has now come
      to a close.  This may be due to a successful completion of the contract,
      or may be early termination due to some non-completion issue.

:period:
    :ref:`Period`

    |ocdsDescription|
    The start and end date for the contract.

:value:
    `Value` object, auto-generated, read-only

    |ocdsDescription|
    The total value of this contract.

:dateSigned:
    string, :ref:`date`, auto-generated

    |ocdsDescription|
    The date when the contract was signed. In the case of multiple signatures, the date of the last signature.
    
    Time frame for `dateSigned`:
    
    * reporting procedure: 
        [24 hours ago - now]
    
    * negotiation/negotiation.quick procedure: 
        [complaint period end - now]

:date:
    string, :ref:`date`

    The date when the contract was changed or activated.

:documents:
    List of :ref:`Document` objects

    |ocdsDescription|
    All documents and attachments related to the contract, including any notices.

Contract workflow
-----------------

.. graphviz::

    digraph G {
        A [ label="pending*" ]
        B [ label="active"]
        C [ label="cancelled"]
         A -> B;
         A -> C;
    }

\* marks initial state
