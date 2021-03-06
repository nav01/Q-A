/*
    Deform doesn't support disabling fields in the schema definition and the hidden flags
    in the colander and widget constructors don't work the way that's needed so CSS is used
    to hide certain fields that depend on another being filled and whatever labels are associated
    with them by default. They are displayed when the appropriate fields/values are filled.
    The containers with classes item-x are generated by deform.
*/
var DEFORM_UNITS_GIVEN = '.item-units_given';
var DEFORM_ACCURACY_DEGREE = '.item-accuracy_degree';
var UNITS_FIELD = '.units-input';
var ACCURACY_SELECTOR = '.math-accuracy-selector';

//Hide units given radio buttons if units field is empty.
function hideUnitsGivenIfUnitsEmpty(node) {
    if (node.value == '') {
        var UNITS_GIVEN_RADIO = '.units-given-radio';
        var $grandparentContainer = $(node).parent().parent();
        var $radioButtons = $grandparentContainer.find(UNITS_GIVEN_RADIO);
        $($radioButtons[0]).prop('checked', false);
        $($radioButtons[1]).prop('checked', false);
        $grandparentContainer.find(DEFORM_UNITS_GIVEN).hide();
    }
}

//Show the units given radio buttons if the units field is non empty.
function showUnitsGivenIfUnitsNotEmpty() {
    var $unitsInputs = $(UNITS_FIELD);
    for (var i = 0; i < $unitsInputs.length; i++) {
        if ($unitsInputs[i].value != '') {
            var $grandparentContainer = $($unitsInputs[i]).parent().parent();
            $grandparentContainer.find(DEFORM_UNITS_GIVEN).show();
        }
    }
}

//Show accuracy degree field if accuracy selector value is non empty and not 'exact'.
function showAccuracyDegreeIfAccuracyNotExact() {
    var $accuracySelectors = $('select' + ACCURACY_SELECTOR); //deform adds classes to the options too
    for (var i = 0; i < $accuracySelectors.length; i++) {
        if ($accuracySelectors[i].value != 'exact' && $accuracySelectors[i].value != '') {
            var $grandparentContainer = $($accuracySelectors[i]).parent().parent();
            $grandparentContainer.find(DEFORM_ACCURACY_DEGREE).show();
        }
    }
}

//Hide/Show accuracy degree based on value of accuracy selector.
$(document).on('change', ACCURACY_SELECTOR, function() {
    var ACCURACY_DEGREE_FIELD = '.math-accuracy-degree';
    var $mathAccuracyDegreeContainer = $(this).parent().parent().find(DEFORM_ACCURACY_DEGREE);
    var $mathAccuracyDegree = $mathAccuracyDegreeContainer.find(ACCURACY_DEGREE_FIELD);
    if (this.value == 'exact' || this.value == '') {
        $mathAccuracyDegree.val('');
        $mathAccuracyDegreeContainer.hide();
    } else
        $mathAccuracyDegreeContainer.show();
});

//Show/Hide the units_given field based on whether the units field is empty or not.
$(document).on('focusin', UNITS_FIELD, function() {
    $(this).parent().parent().find(DEFORM_UNITS_GIVEN).show();
});

$(document).on('focusout', UNITS_FIELD, function() {
    hideUnitsGivenIfUnitsEmpty(this);
});

$(document).ready(function() {
    showUnitsGivenIfUnitsNotEmpty();
    showAccuracyDegreeIfAccuracyNotExact();
});
