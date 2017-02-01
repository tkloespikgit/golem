
class TestGNT:
    INIT_HEX = "606060405234610000575b610548806100196000396000f300606060405236156100725763ffffffff60e060020a60003504166306fdde03811461007757806318160ddd14610104578063313ce5671461012357806370a082311461014657806395d89b4114610171578063a9059cbb146101fe578063efc81a8c1461022e578063fa369e661461023d575b610000565b3461000057610084610257565b6040805160208082528351818301528351919283929083019185019080838382156100ca575b8051825260208311156100ca57601f1990920191602091820191016100aa565b505050905090810190601f1680156100f65780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b346100005761011161028e565b60408051918252519081900360200190f35b3461000057610130610294565b6040805160ff9092168252519081900360200190f35b3461000057610111600160a060020a0360043516610299565b60408051918252519081900360200190f35b34610000576100846102b8565b6040805160208082528351818301528351919283929083019185019080838382156100ca575b8051825260208311156100ca57601f1990920191602091820191016100aa565b505050905090810190601f1680156100f65780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b346100005761021a600160a060020a03600435166024356102ef565b604080519115158252519081900360200190f35b346100005761023b61039a565b005b346100005761023b6004803560248101910135610427565b005b60408051808201909152601881527f5465737420476f6c656d204e6574776f726b20546f6b656e0000000000000000602082015281565b60005481565b601281565b600160a060020a0381166000908152600160205260409020545b919050565b60408051808201909152600481527f74474e5400000000000000000000000000000000000000000000000000000000602082015281565b600160a060020a0333166000908152600160205260408120548281108015906103185750600083115b1561038e57600160a060020a0333811660008181526001602090815260408083209588900395869055938816808352918490208054880190558351878152935191937fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef929081900390910190a360019150610393565b600091505b5092915050565b600160a060020a033316600090815260016020526040902054683635c9adc5dea00000908190106103ca57610000565b600160a060020a0333166000818152600160209081526040808320805486019055825485018355805185815290517fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef929181900390910190a35b50565b600160a060020a033316600090815260016020526040812054908080805b858410156104f7578686858181101561000057602002919091013593508392505074010000000000000000000000000000000000000000820490508481111561048d57610000565b600160a060020a0380831660008181526001602090815260409182902080548601905581518581529151988590039892933316927fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9281900390910190a35b836001019350610445565b600160a060020a03331660009081526001602052604090208590555b505050505050505600a165627a7a72305820740f23cc4a58537fc84587d3b988c59bf19f7022eebdce6da87ee382c02a3f2a0029"  # noqa
    ABI = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"create","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"payments","type":"bytes32[]"}],"name":"batchTransfer","outputs":[],"payable":false,"type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Transfer","type":"event"}]'  # noqa
