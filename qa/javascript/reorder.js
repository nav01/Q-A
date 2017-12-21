$(document).ready(function () {
    $(function () {
        $('ol.sortable').sortable();
    });

    $('#reorder').submit(function (){
        var resourceIdPrefix = 'reorderable-';
        var inputReorderableIdNamePrefix = 'reorderable_';
        var resourceList = $('[id^=' + resourceIdPrefix + ']');
        var inputList = $('[id^=' + inputReorderableIdNamePrefix + ']');
        for(var i = 0; i < inputList.length; i++){
            var resourceId = $(resourceList[i]).attr('id').replace(resourceIdPrefix, '');
            $(inputList[i]).attr('value', resourceId);
        }
        console.log('suh');
        return true;
    });

});
