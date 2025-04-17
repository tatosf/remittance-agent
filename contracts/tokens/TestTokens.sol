// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title TestToken
 * @dev A simple ERC20 token with minting capabilities for testing remittance flows
 */
contract TestToken {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    
    mapping(address => uint256) private balances;
    mapping(address => mapping(address => uint256)) private allowances;
    
    address public owner;
    
    // Events
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 amount);
    
    /**
     * @dev Constructor to create a new TestToken
     * @param _name The name of the token
     * @param _symbol The symbol of the token
     * @param _decimals The number of decimals the token uses
     */
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
        owner = msg.sender;
    }
    
    /**
     * @dev Modifier to restrict certain functions to the owner
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "TestToken: caller is not the owner");
        _;
    }
    
    /**
     * @dev Gets the balance of the specified address
     * @param account The address to query the balance of
     * @return A uint256 representing the amount owned by the passed address
     */
    function balanceOf(address account) external view returns (uint256) {
        return balances[account];
    }
    
    /**
     * @dev Transfer tokens to a specified address
     * @param to The address to transfer to
     * @param amount The amount to be transferred
     * @return A boolean that indicates if the operation was successful
     */
    function transfer(address to, uint256 amount) external returns (bool) {
        require(to != address(0), "TestToken: transfer to the zero address");
        
        uint256 senderBalance = balances[msg.sender];
        require(senderBalance >= amount, "TestToken: transfer amount exceeds balance");
        
        balances[msg.sender] = senderBalance - amount;
        balances[to] += amount;
        
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    /**
     * @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender
     * @param spender The address which will spend the funds
     * @param amount The amount of tokens to be spent
     * @return A boolean that indicates if the operation was successful
     */
    function approve(address spender, uint256 amount) external returns (bool) {
        require(spender != address(0), "TestToken: approve to the zero address");
        
        allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    /**
     * @dev Returns the amount of tokens that an owner allowed to a spender
     * @param accountOwner The address which owns the funds
     * @param spender The address which will spend the funds
     * @return A uint256 specifying the amount of tokens still available for the spender
     */
    function allowance(address accountOwner, address spender) external view returns (uint256) {
        return allowances[accountOwner][spender];
    }
    
    /**
     * @dev Transfer tokens from one address to another
     * @param from The address which you want to send tokens from
     * @param to The address which you want to transfer to
     * @param amount The amount of tokens to be transferred
     * @return A boolean that indicates if the operation was successful
     */
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(from != address(0), "TestToken: transfer from the zero address");
        require(to != address(0), "TestToken: transfer to the zero address");
        
        uint256 currentAllowance = allowances[from][msg.sender];
        require(currentAllowance >= amount, "TestToken: transfer amount exceeds allowance");
        
        uint256 fromBalance = balances[from];
        require(fromBalance >= amount, "TestToken: transfer amount exceeds balance");
        
        allowances[from][msg.sender] = currentAllowance - amount;
        balances[from] = fromBalance - amount;
        balances[to] += amount;
        
        emit Transfer(from, to, amount);
        return true;
    }
    
    /**
     * @dev Mint new tokens
     * @param to The address that will receive the minted tokens
     * @param amount The amount of tokens to mint
     * @return A boolean that indicates if the operation was successful
     */
    function mint(address to, uint256 amount) external onlyOwner returns (bool) {
        require(to != address(0), "TestToken: mint to the zero address");
        
        totalSupply += amount;
        balances[to] += amount;
        
        emit Mint(to, amount);
        emit Transfer(address(0), to, amount);
        return true;
    }
    
    /**
     * @dev Function to enable anyone to get test tokens for testing purposes
     * @param amount The amount of tokens to request
     * @return A boolean that indicates if the operation was successful
     */
    function faucet(uint256 amount) external returns (bool) {
        require(amount <= 1000 * 10**uint256(decimals), "TestToken: faucet amount exceeds maximum allowed");
        
        totalSupply += amount;
        balances[msg.sender] += amount;
        
        emit Mint(msg.sender, amount);
        emit Transfer(address(0), msg.sender, amount);
        return true;
    }
} 