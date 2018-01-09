$(document).ready(function () {
    $(function () {
        $('ol.sortable').sortable();
    });
    /*
    Reorder a set's questions through ajax.
    The order is set by the user dragging questions to their desired order. The
    submit function modifies the input values to reflect the new order before
    submitting the ajax request.
    */
    $('#reorder').submit(function (event){
        event.preventDefault();
        var resourceIdPrefix = 'reorderable-';
        var inputReorderableIdNamePrefix = 'reorderable_';
        var resourceList = $('[id^=' + resourceIdPrefix + ']');
        var inputList = $('[id^=' + inputReorderableIdNamePrefix + ']');

        if(resourceList.length == 0){
            alert('There are no questions to sort.');
            $(this).find(':submit').hide();
            return;
        } else if (resourceList.length < inputList.length){
            //Get rid of extra input tags, if questions are deleted.
            for(var i = inputList.length - 1; i > resourceList.length - 1; i--)
                $(inputList[i]).remove();
            inputList.splice(resourceList.length, inputList.length - resourceList.length);
        }
        //Assign new values to input tags based on question order
        for(var i = 0; i < inputList.length; i++){
            var resourceId = $(resourceList[i]).attr('id').replace(resourceIdPrefix, '');
            $(inputList[i]).attr('value', resourceId);
        }
        var formData = $(this).serialize();
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: formData,
        }).done(function(){
            $('.qr-success').show();
            $('.qr-success').fadeOut(10000);
            $('.qr-failure').hide();
        }).fail(function(){
            $('.qr-success').hide();
            $('.qr-failure').show();
            $('.qr-failure').fadeOut(10000);
        });
    });

});
