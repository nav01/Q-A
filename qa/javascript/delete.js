/*
    Delete resources via ajax.
*/
$(document).ready(function(){
    $('.delete-form').submit(function(event) {
        var form = this;
        event.preventDefault();
        var formData = $(this).serialize();
        Object.assign(formData, {ajax: true});
        $.ajax({
            type: 'POST',
            url: $(form).attr('action'),
            data: formData + '&ajax=true',
        }).done(function(data, statusText, xhr){
            if(xhr.status == '204'){
                resource = $(form).closest('.resource-container');
                resource_name = $(resource).attr('data-name');
                resource_type = $(resource).attr('data-type');
                $(resource).remove();
                window.dispatchEvent(new CustomEvent('deleteResource', {detail: {resource_name: resource_name, resource_type: resource_type}}));
            }
        }).fail(function(xhr, statusText, errorThrown){
            if (xhr.status == '401') {
                window.location = xhr.responseText;
            } else {
                alert('You do not have the appropriate permissions to perform that operation.');
            }
        });
    });
});
