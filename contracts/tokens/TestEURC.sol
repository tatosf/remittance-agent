// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TestEURC
 * @dev An ERC20 token that simulates EURC for testing purposes
 * It has a mint function that can be called by anyone to mint tokens to themselves
 * This makes it easy to get test tokens without relying on faucets
 */
contract TestEURC is ERC20, Ownable {
    uint8 private constant _decimals = 6;
    
    constructor() 
        ERC20("Test Euro Coin", "tEURC") 
        Ownable(msg.sender)
    {
        // Mint initial supply to the deployer
        _mint(msg.sender, 1000000 * 10**_decimals); // 1 million tEURC
    }
    
    function decimals() public pure override returns (uint8) {
        return _decimals;
    }
    
    /**
     * @dev Public mint function that anyone can call to mint tokens to themselves
     * This is only for testing and would not exist in a real stablecoin
     * @param amount Amount of tokens to mint (in the smallest unit, e.g., 1000000 = 1 tEURC)
     */
    function mint(uint256 amount) external {
        require(amount <= 10000 * 10**_decimals, "Can't mint more than 10,000 tEURC at once");
        _mint(msg.sender, amount);
    }
    
    /**
     * @dev Public mint function that mints tokens to the specified address
     * This is useful for testing remittance scenarios
     * @param to Address to receive the tokens
     * @param amount Amount of tokens to mint (in the smallest unit)
     */
    function mintTo(address to, uint256 amount) external {
        require(amount <= 10000 * 10**_decimals, "Can't mint more than 10,000 tEURC at once");
        _mint(to, amount);
    }
    
    /**
     * @dev Owner-only function to mint arbitrary amounts
     * @param to Address to receive the tokens
     * @param amount Amount of tokens to mint
     */
    function ownerMint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
    
    /**
     * @dev Burns tokens from the caller's balance
     * @param amount Amount of tokens to burn
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
} 